#!/usr/bin/env bash
set -euo pipefail
cd /home/nebius/downproj-repro
export PATH="$PWD/venv/bin:/usr/local/cuda/bin:$PATH"
export CUDA_HOME=/usr/local/cuda
export MAX_JOBS=8
export OMP_NUM_THREADS=1
export TVM_FFI_CUDA_ARCH_LIST=10.3a
timeout 600 nsys profile --trace=cuda,nvtx --sample=none --cpuctxsw=none \
  --capture-range=cudaProfilerApi --capture-range-end=stop \
  --force-overwrite=true -o steady \
  python repro_benchmark.py --reference-js sweep-data.js \
    --quant-source quant_source --output steady_meta.json
timeout 180 nsys export --type sqlite --force-overwrite=true --output steady.sqlite steady.nsys-rep
