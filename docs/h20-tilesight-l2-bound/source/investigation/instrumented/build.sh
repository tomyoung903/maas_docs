#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${CUTLASS_ROOT:?Set CUTLASS_ROOT to pinned CUTLASS}"
NVCC_BIN=${NVCC_BIN:-nvcc}
ENABLE_PHASE_TRACE=${ENABLE_PHASE_TRACE:-1}
case "$ENABLE_PHASE_TRACE" in 0|1) ;; *) echo 'ENABLE_PHASE_TRACE must be 0 or 1' >&2; exit 2;; esac
OUT_DIR=${OUT_DIR:-build/trace${ENABLE_PHASE_TRACE}}
mkdir -p "$OUT_DIR"
CUDA_VISIBLE_DEVICES='' "$NVCC_BIN" -std=c++17 -O3 -DNDEBUG -arch=sm_90a \
  --expt-relaxed-constexpr -DENABLE_PHASE_TRACE="$ENABLE_PHASE_TRACE" \
  -Iinclude -I"$CUTLASS_ROOT/include" -Xptxas=-v \
  benchmark.cu -lcublas -o "$OUT_DIR/benchmark" >"$OUT_DIR/build.log" 2>&1
sha256sum benchmark.cu include/cutlass/gemm/kernel/gemm.h "$OUT_DIR/benchmark" >"$OUT_DIR/SHA256SUMS"
