#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
NVCC_BIN=${NVCC_BIN:-nvcc}
CUDA_VISIBLE_DEVICES='' "$NVCC_BIN" -std=c++17 -O3 -DNDEBUG -arch=sm_90a \
  -lineinfo -Xptxas=-v probe.cu -o probe >build.log 2>&1
sha256sum probe.cu probe >SHA256SUMS
