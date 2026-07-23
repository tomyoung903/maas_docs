#!/usr/bin/env python3
"""Standalone synthetic reproducer for GLM-5.2 TRT-LLM sparse MLA."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

import torch
from flashinfer.decode import trtllm_batch_decode_with_kv_cache_mla


FP8_DENSE_PEAK_TFLOPS = 4_500.0
QK_NOPE_HEAD_DIM = 128
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM
VALUE_DIM = KV_LORA_RANK
PAGE_SIZE = 64
WORKSPACE_BYTES = 384 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Invoke the exact FlashInfer TRT-LLM sparse-MLA entry point used by "
            "the measured GLM-5.2 DSA prefill kernel."
        )
    )
    parser.add_argument("--tokens", type=int, default=16_384)
    parser.add_argument("--topk", type=int, default=2_048)
    parser.add_argument("--heads", type=int, default=64)
    parser.add_argument(
        "--layout",
        choices=("recent", "spread"),
        default="recent",
        help="Synthetic selected-KV layout. Cardinality is identical in both modes.",
    )
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def build_page_table(tokens: int, topk: int, layout: str) -> torch.Tensor:
    """Return [tokens, 1, topk] physical token indices, padded with -1."""
    rows = torch.arange(tokens, dtype=torch.int32, device="cuda").unsqueeze(1)
    cols = torch.arange(topk, dtype=torch.int32, device="cuda").unsqueeze(0)
    valid_count = torch.minimum(rows + 1, torch.tensor(topk, device="cuda"))
    first_valid_col = topk - valid_count
    rank = cols - first_valid_col
    valid = rank >= 0

    if layout == "recent":
        indices = rows - valid_count + 1 + rank
    else:
        # Keep the exact same number of selected pairs, but distribute them over
        # the complete causal prefix instead of taking the most recent tail.
        indices = torch.div(rank * (rows + 1), valid_count, rounding_mode="floor")
        indices = torch.minimum(indices, rows)

    indices = torch.where(valid, indices, torch.full_like(indices, -1))
    return indices.unsqueeze(1).contiguous()


def selected_pairs(tokens: int, topk: int) -> int:
    dense_prefix = min(tokens, topk)
    return dense_prefix * (dense_prefix + 1) // 2 + max(tokens - topk, 0) * topk


def useful_fp8_flops(tokens: int, topk: int, heads: int) -> int:
    # For every selected query/KV pair and head:
    #   Q dot K: 2 * (512 + 64)
    #   probability times V: 2 * 512
    return selected_pairs(tokens, topk) * heads * 2 * (2 * KV_LORA_RANK + QK_ROPE_HEAD_DIM)


def main() -> None:
    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required")
    if args.tokens <= 0 or args.topk <= 0 or args.heads <= 0:
        raise ValueError("tokens, topk, and heads must be positive")
    if args.topk > args.tokens:
        raise ValueError("this causal reproducer requires topk <= tokens")

    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.set_grad_enabled(False)

    device = torch.device("cuda")
    fp8 = torch.float8_e4m3fn
    num_pages = math.ceil(args.tokens / PAGE_SIZE)

    # Constant values isolate scheduling and memory-layout behavior. The kernel's
    # launch geometry and memory addresses depend on shapes and page indices, not
    # on the random distribution used to populate Q/K/V.
    query = torch.full(
        (args.tokens, 1, args.heads, HEAD_DIM),
        0.0625,
        dtype=fp8,
        device=device,
    )
    kv_cache = torch.full(
        (num_pages, 1, PAGE_SIZE, HEAD_DIM),
        0.03125,
        dtype=fp8,
        device=device,
    )
    page_table = build_page_table(args.tokens, args.topk, args.layout)
    seq_lens = torch.arange(1, args.tokens + 1, dtype=torch.int32, device=device)
    seq_lens.clamp_(max=args.topk)
    workspace = torch.zeros(WORKSPACE_BYTES, dtype=torch.uint8, device=device)
    out = torch.empty(
        (args.tokens, 1, args.heads, VALUE_DIM),
        dtype=torch.bfloat16,
        device=device,
    )

    def invoke() -> torch.Tensor:
        return trtllm_batch_decode_with_kv_cache_mla(
            query=query,
            kv_cache=kv_cache,
            workspace_buffer=workspace,
            qk_nope_head_dim=QK_NOPE_HEAD_DIM,
            kv_lora_rank=KV_LORA_RANK,
            qk_rope_head_dim=QK_ROPE_HEAD_DIM,
            block_tables=page_table,
            seq_lens=seq_lens,
            max_seq_len=args.tokens,
            sparse_mla_top_k=args.topk,
            out=out,
            bmm1_scale=1.0 / math.sqrt(QK_NOPE_HEAD_DIM + QK_ROPE_HEAD_DIM),
            bmm2_scale=1.0,
            backend="trtllm-gen",
            is_var_seq=True,
            uses_shared_paged_kv_idx=True,
        )

    for _ in range(args.warmup):
        invoke()
    torch.cuda.synchronize()

    group_ms: list[float] = []
    torch.cuda.nvtx.range_push("sparse_mla_measurement")
    for _ in range(args.repeats):
        start = torch.cuda.Event(enable_timing=True)
        stop = torch.cuda.Event(enable_timing=True)
        start.record()
        for _ in range(args.iterations):
            invoke()
        stop.record()
        stop.synchronize()
        group_ms.append(start.elapsed_time(stop) / args.iterations)
    torch.cuda.nvtx.range_pop()
    torch.cuda.synchronize()

    sample = out[:: max(args.tokens // 16, 1), 0, 0, :16].float()
    if not torch.isfinite(sample).all():
        raise RuntimeError("kernel output sample contains non-finite values")

    work_flops = useful_fp8_flops(args.tokens, args.topk, args.heads)
    median_ms = statistics.median(group_ms)
    event_mfu = work_flops / (median_ms / 1_000.0) / (
        FP8_DENSE_PEAK_TFLOPS * 1_000_000_000_000
    )
    result = {
        "contract": {
            "entry_point": (
                "flashinfer.decode.trtllm_batch_decode_with_kv_cache_mla"
            ),
            "backend": "trtllm-gen",
            "tokens": args.tokens,
            "topk": args.topk,
            "heads": args.heads,
            "qk_nope_head_dim": QK_NOPE_HEAD_DIM,
            "kv_lora_rank": KV_LORA_RANK,
            "qk_rope_head_dim": QK_ROPE_HEAD_DIM,
            "value_dim": VALUE_DIM,
            "page_size": PAGE_SIZE,
            "layout": args.layout,
            "query_shape": list(query.shape),
            "kv_cache_shape": list(kv_cache.shape),
            "page_table_shape": list(page_table.shape),
            "seq_lens_shape": list(seq_lens.shape),
            "query_dtype": str(query.dtype),
            "kv_cache_dtype": str(kv_cache.dtype),
            "output_dtype": str(out.dtype),
        },
        "work": {
            "selected_pairs": selected_pairs(args.tokens, args.topk),
            "useful_fp8_flops_per_launch": work_flops,
            "useful_fp8_tflop_per_launch": work_flops / 1_000_000_000_000,
            "normalization_peak_tflops": FP8_DENSE_PEAK_TFLOPS,
        },
        "timing": {
            "warmup": args.warmup,
            "iterations_per_repeat": args.iterations,
            "repeats": args.repeats,
            "cuda_event_ms_per_launch": group_ms,
            "cuda_event_median_ms": median_ms,
            "cuda_event_normalized_mfu_percent": event_mfu * 100.0,
        },
        "validation": {
            "sample_finite": True,
            "sample_mean": sample.mean().item(),
            "device_name": torch.cuda.get_device_name(),
            "compute_capability": list(torch.cuda.get_device_capability()),
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "max_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
        },
    }

    payload = json.dumps(result, indent=2) + "\n"
    print(payload, end="")
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload)


if __name__ == "__main__":
    main()
