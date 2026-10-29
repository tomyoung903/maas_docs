# Dense-down timing reproduction

This record measures one FP8 dense-down projection on one B300, with `N=6144`,
`K=1536` and the 259 `M` values in `sweep-data.js`.

The recorded run used Ubuntu 24.04 x86_64, Python 3.12.3, CUDA toolkit 13.0.88,
NVIDIA driver 580.173.02, PyTorch 2.11.0+cu130, and Nsight Systems 2025.3.2.
`setup-b300-bench.sh` installs the Python dependencies and builds DeepGEMM at
`b4296edce3cd07e3b6392c8eb390cee9c41a6b70`. The package declares 2.5.0; the original
tutorial calls this source revision v0.1.3. The quantizer is a newer isolated
SGLang v2 JIT port, not a byte-identical copy of the original production kernel.

Copy the benchmark, `quant_source/`, parser and `sweep-data.js` into the created
`/home/nebius/downproj-repro` directory. The included run scripts preserve the
historical invocation. For a new run, explicitly override the benchmark's
historical cutoff instead of reusing its October 29 deadline:

```bash
cd /home/nebius/downproj-repro
export PATH="$PWD/venv/bin:/usr/local/cuda/bin:$PATH"
export CUDA_HOME=/usr/local/cuda
export MAX_JOBS=8 OMP_NUM_THREADS=1 TVM_FFI_CUDA_ARCH_LIST=10.3a
deadline=$(python -c 'import time; print(int(time.time()) + 1200)')
nsys profile --trace=cuda,nvtx --sample=none --cpuctxsw=none \
  --capture-range=cudaProfilerApi --capture-range-end=stop \
  --force-overwrite=true -o rerun \
  python repro_benchmark.py --reference-js sweep-data.js \
    --quant-source quant_source --output rerun_meta.json \
    --deadline-epoch "$deadline"
nsys export --type sqlite --force-overwrite=true \
  --output rerun.sqlite rerun.nsys-rep
python parse_dense_down_nsys.py rerun.sqlite --metadata rerun_meta.json \
  --reference-js sweep-data.js --output rerun_results.json --csv rerun_results.csv
```

Each shape gets one JIT/correctness preflight and three immediate warmups before
30 measured invocations. The parser owns kernels through the NVTX CPU range's
CUDA launch correlations, requires exactly one quantization and one GEMM kernel,
and computes the union of their GPU intervals. It excludes host launch gaps;
CUDA-event elapsed time is not a replacement for this metric. No L2 flush is used.

The published results retain per-sample start/end timestamps and durations.
The complete original Nsight traces and SQLite exports are retained in the local
task's `outputs/b300-reproduction/results-bundle.tar.gz`. Its SHA256 is
`6d240398817cae7a3a5215c86ad14168bee7e1c8941c05f0fc32465192fc70dc`.

To regenerate the static report from downloaded results, keep `reference.json`
beside `build_b300_report.py`, then run:

```bash
python build_b300_report.py --input ../results.json --output ./rendered
```

The measured operation, matrix dimensions and GPU-active metric match the
reference; hardware, architecture and the quantizer build differ. Treat this as
a controlled reimplementation, not an exact replay or a pure hardware A/B test.
