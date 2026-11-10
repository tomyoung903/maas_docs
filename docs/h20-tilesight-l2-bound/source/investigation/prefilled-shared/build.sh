#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${CUTLASS_ROOT:?Set CUTLASS_ROOT to revision 954c8d7be60d730cc3f51e8f1ffe9850dce054d5}"
NVCC_BIN=${NVCC_BIN:-nvcc}
mkdir -p build
CUDA_VISIBLE_DEVICES='' "$NVCC_BIN" -std=c++17 -O3 -DNDEBUG -arch=sm_90a \
  --expt-relaxed-constexpr -DPIPELINE_STAGES=3 \
  -Iinclude -I"$CUTLASS_ROOT/include" \
  -Xptxas=-v -lineinfo benchmark.cu -lcublas -o build/benchmark >build/build.log 2>&1
sha256sum benchmark.cu include/prefill_control.cuh \
  include/cutlass/gemm/threadblock/mma_multistage.h build/benchmark >build/SHA256SUMS
