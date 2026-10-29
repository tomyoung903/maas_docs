#!/usr/bin/env python3
"""Dense-down FP8 composite sweep. Timing is obtained from an Nsight trace.

The default quantizer is an isolated SGLang v2 JIT port; its source identity is
recorded and explicitly differs from the retained GB300 production image.
No CUDA-event elapsed time is reported as device kernel time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import time

import torch
import deep_gemm


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_quantizer(source: Path, build_dir: Path):
    import tvm_ffi
    import tvm_ffi.cpp
    major, minor = torch.cuda.get_device_capability(0)
    # This SGLang header requires an exact __CUDA_ARCH__ match. Do not add a
    # second SM100a target to an SM103 build: the static assertion rejects it.
    cuda_arch = major * 100 + minor * 10
    os.environ["TVM_FFI_CUDA_ARCH_LIST"] = f"{major}.{minor}a"
    define = f"-DSGL_CUDA_ARCH={cuda_arch}"
    build_dir.mkdir(parents=True, exist_ok=True)
    wrapper = build_dir / "quant_wrapper.cu"
    wrapper.write_text('''#include <tvm/ffi/container/tensor.h>
#include <tvm/ffi/dtype.h>
#include <tvm/ffi/error.h>
#include <tvm/ffi/extra/c_env_api.h>
#include <tvm/ffi/function.h>
#include "per_token_group_quant_8bit_v2.cuh"
namespace sglang {
TVM_FFI_DLL_EXPORT_TYPED_FUNC(quantize,
  (PerTokenGroupQuant8bitV2Kernel<__nv_bfloat16, __nv_fp8_e4m3, true>::run));
}
''')
    built = tvm_ffi.cpp.build(
        name="dense_down_quant_v2",
        cuda_files=[str(wrapper)],
        extra_cflags=["-std=c++20", "-O3", define],
        extra_cuda_cflags=["-std=c++20", "-O3", "--use_fast_math", "--expt-relaxed-constexpr", define],
        extra_include_paths=[str(source), str(source / "include")],
        build_directory=str(build_dir),
    )
    module = tvm_ffi.load_module(built)

    def quantize(x):
        m, k = x.shape
        q = torch.empty((m, k), dtype=torch.float8_e4m3fn, device=x.device)
        # Same scale layout as SGLang: packed uint8 exponents in INT32;
        # MN-major, with M padded to a multiple of four for TMA alignment.
        s = torch.empty(((k // 128 + 3) // 4, (m + 3) // 4 * 4),
                        dtype=torch.int32, device=x.device).t()[:m]
        module.quantize(x, q, s, x, 128, True, False, False,
                        m * (k // 128), 1, True, k // 128, m, 0, s.stride(-1))
        return q, s

    return quantize


def make_weight(n, k):
    w = torch.randn((n, k), dtype=torch.bfloat16, device="cuda")
    view = w.view(n // 128, 128, k // 128, 128)
    amax = view.abs().float().amax((1, 3), keepdim=True).clamp_min(1e-4)
    sf = torch.pow(2.0, torch.ceil(torch.log2(amax / 448.0)))
    wq = (view.float() / sf).to(torch.float8_e4m3fn).view(n, k).contiguous()
    block_sf = sf.view(n // 128, k // 128)
    expanded_sf = block_sf.repeat_interleave(128, dim=0).contiguous()
    from deep_gemm.utils.layout import get_mn_major_tma_aligned_packed_ue8m0_tensor
    packed = get_mn_major_tma_aligned_packed_ue8m0_tensor(expanded_sf)
    return w, wq, packed, expanded_sf


def correctness(x, aq, a_s, w, wq, w_sf, out):
    raw_exp = a_s.contiguous().view(torch.uint8)[:, :x.shape[1] // 128]
    a_sf = torch.pow(2.0, raw_exp.float() - 127.0)
    x_dq = aq.float() * a_sf.repeat_interleave(128, dim=1)
    w_dq = wq.float() * w_sf.repeat_interleave(128, dim=1)
    ref_quant = x_dq @ w_dq.t()
    ref_bf16 = x.float() @ w.float().t()
    result = out.float()
    rel_quant = ((result - ref_quant).norm() / ref_quant.norm()).item()
    rel_bf16 = ((result - ref_bf16).norm() / ref_bf16.norm()).item()
    finite = bool(torch.isfinite(result).all())
    if not finite or rel_quant > 0.012 or rel_bf16 > 0.12:
        raise RuntimeError(f"Correctness failed: finite={finite}, quant_l2={rel_quant}, bf16_l2={rel_bf16}")
    return {"finite": finite, "relative_l2_vs_quantized_fp32": rel_quant,
            "relative_l2_vs_unquantized_bf16_fp32": rel_bf16}


def parse_ms(args):
    if args.m:
        return [int(v) for v in args.m.split(",")]
    data = Path(args.reference_js).read_text()
    rows = re.findall(r"^\s*\[(\d+),", data, re.M)
    if not rows:
        raise RuntimeError("Reference JS contains no sweep rows")
    return list(map(int, rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", help="Comma-separated M values; otherwise reference JS full sweep")
    ap.add_argument("--reference-js", default="sweep-data.js")
    ap.add_argument("--quant-source", default="quant_source")
    ap.add_argument("--build-dir", default="quant_build")
    ap.add_argument("--output", default="run_metadata.json")
    ap.add_argument("--warmups", type=int, default=3)
    ap.add_argument("--samples", type=int, default=30)
    ap.add_argument("--deadline-epoch", type=float, default=1793268000.0,
                    help="Hard benchmark cutoff, default 2026-10-29 10:00 UTC")
    args = ap.parse_args()
    n, k = 6144, 1536
    torch.manual_seed(20261029)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_num_threads(1)
    ms = parse_ms(args)
    quant_source = Path(args.quant_source).resolve()
    quant = load_quantizer(quant_source, Path(args.build_dir).resolve())
    w, wq, ws, wsf = make_weight(n, k)
    props = torch.cuda.get_device_properties(0)
    meta = {"schema_version": "b300-dense-down-reproduction-v1",
            "m_values": ms, "n": n, "k": k, "warmups": args.warmups,
            "samples_per_shape": args.samples, "started_epoch": time.time(),
            "warmup_policy": "one JIT/correctness preflight call, then three immediate pre-measurement warmups for each shape",
            "torch": torch.__version__, "torch_cuda": torch.version.cuda,
            "deep_gemm_version": getattr(deep_gemm, "__version__", "unknown"),
            "python": platform.python_version(), "platform": platform.platform(),
            "device_name": props.name, "sm_count": props.multi_processor_count,
            "compute_capability": list(torch.cuda.get_device_capability(0)),
            "seed": 20261029, "cpu_architecture": platform.machine(),
            "deepgemm_commit": subprocess.check_output(
                ["git", "-C", "DeepGEMM", "rev-parse", "HEAD"], text=True).strip(),
            "benchmark_source_sha256": sha256(__file__),
            "compute_capability": list(torch.cuda.get_device_capability(0)),
            "quant_compile_arch": os.environ["TVM_FFI_CUDA_ARCH_LIST"],
            "quant_source_sha256": sha256(quant_source / "per_token_group_quant_8bit_v2.cuh"),
            "quant_identity": "SGLang isolated v2 JIT port; source differs from original production artifact",
            "measurement": "Nsight correlation-owned GPU-active interval union, two kernels per NVTX sample",
            "input_model": "seeded synthetic fixed CUDA-resident tensors; no L2 flush; no H2D in samples",
            "correctness": {}, "completed_m_values": []}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(meta, indent=2) + "\n")
    save()
    cases = []
    for m in ms:
        if time.time() >= args.deadline_epoch:
            meta["status"] = "cutoff_during_warmup"; save(); return
        x = torch.randn((m, k), dtype=torch.bfloat16, device="cuda")
        out = torch.empty((m, n), dtype=torch.bfloat16, device="cuda")
        for _ in range(1):
            aq, a_s = quant(x)
            deep_gemm.fp8_gemm_nt((aq, a_s), (wq, ws), out)
        torch.cuda.synchronize()
        # Verify every prepared case outside capture; GEMM reference computation
        # is excluded from all sample ranges and subsequent Nsight capture.
        if m in (1, 10, 100, 500, 2000, 10000) or len(ms) <= 10:
            meta["correctness"][str(m)] = correctness(x, aq, a_s, w, wq, wsf, out)
        cases.append((m, x, out))
        print(json.dumps({"phase": "prepared", "m": m}), flush=True)
    torch.cuda.synchronize()
    meta["warmup_finished_epoch"] = time.time(); save()
    torch.cuda.cudart().cudaProfilerStart()
    try:
        for m, x, out in cases:
            if time.time() >= args.deadline_epoch:
                meta["status"] = "cutoff_during_measurement"; break
            # Refresh this exact shape immediately before its measurements.
            # These calls are outside the owned sample ranges and excluded.
            for _ in range(args.warmups):
                aq, a_s = quant(x)
                deep_gemm.fp8_gemm_nt((aq, a_s), (wq, ws), out)
            torch.cuda.synchronize()
            for sample in range(args.samples):
                torch.cuda.synchronize()
                torch.cuda.nvtx.range_push(f"dense_down/m={m}/sample={sample}")
                aq, a_s = quant(x)
                deep_gemm.fp8_gemm_nt((aq, a_s), (wq, ws), out)
                torch.cuda.nvtx.range_pop()
                torch.cuda.synchronize()
            meta["completed_m_values"].append(m)
            print(json.dumps({"phase": "measured", "m": m}), flush=True)
            save()
        else:
            meta["status"] = "complete"
    finally:
        torch.cuda.synchronize()
        torch.cuda.cudart().cudaProfilerStop()
        meta["finished_epoch"] = time.time(); save()


if __name__ == "__main__":
    main()
