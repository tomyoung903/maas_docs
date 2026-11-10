#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${CUTLASS_ROOT:?Set CUTLASS_ROOT to the pinned CUTLASS checkout}"
NVCC_BIN=${NVCC_BIN:-nvcc}
CUDA_VISIBLE_DEVICES='' "$NVCC_BIN" -std=c++17 -O3 -DNDEBUG -arch=sm_90a \
  --expt-relaxed-constexpr -Iinclude -I"$CUTLASS_ROOT/include" \
  -Xptxas=-v benchmark.cu -lcublas -o benchmark >build.log 2>&1
