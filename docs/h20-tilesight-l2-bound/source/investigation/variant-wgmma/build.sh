#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${CUTLASS_ROOT:?Set CUTLASS_ROOT to pinned CUTLASS}"
NVCC_BIN=${NVCC_BIN:-nvcc}
PIPELINE_STAGES=${PIPELINE_STAGES:-3}
case "$PIPELINE_STAGES" in 2|3|4|5) ;; *) echo 'PIPELINE_STAGES must be 2,3,4,5' >&2; exit 2;; esac
OUT_DIR=${OUT_DIR:-build/stages${PIPELINE_STAGES}}
mkdir -p "$OUT_DIR"
CUDA_VISIBLE_DEVICES='' "$NVCC_BIN" -std=c++17 -O3 -DNDEBUG -arch=sm_90a \
  --expt-relaxed-constexpr -DPIPELINE_STAGES="$PIPELINE_STAGES" \
  -Iinclude -I"$CUTLASS_ROOT/include" -Xptxas=-v \
  benchmark.cu -lcublas -o "$OUT_DIR/benchmark" >"$OUT_DIR/build.log" 2>&1
sha256sum benchmark.cu "$OUT_DIR/benchmark" >"$OUT_DIR/SHA256SUMS"
