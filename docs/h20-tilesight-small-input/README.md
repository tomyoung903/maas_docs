# Smaller H20 input: TileSight model walkthrough

M=16, N=26,624, K=2,752. FP16 inputs/output, FP32 accumulation.
The page uses the same presentation as the larger memory-bound walkthrough,
with numbers extracted from this shape's saved prediction rather than scaled
from the previous answer.

- 208 output CTAs, each 16×128, with 43 K steps of 64.
- Four maximum resident CTAs/SM, 78 SMs, 312 possible slots.
- The model packs the partial wave into 52 active SMs. This is not measured CTA placement.
- Global HBM/L2 rates are shared by 208 concurrent CTAs; on-chip compute/shared rates use 4 CTAs per SM.
- Selected II = 0.935157523691µs.
- Kernel-body prediction 41.063650671442µs.
- Read-only eviction measurement 42.080µs, prediction 2.42% lower.
- Write-based eviction measurement 52.032µs retained as a separate cache-state condition.

All sample CSVs are normalized to LF; numeric values are unchanged. The page
generator verifies their 51 samples per condition and medians, operation counts,
the overlap schedule and the full-grid result. It does not rerun a GPU job.

## Regenerate

From the MaaS Docs repository root:

```sh
python3 tools/h20_tilesight_small_input/build.py
```

## Reproduce the CPU prediction

Use the recorded TileSight revision 6673bc3941d23572caad5d25473c9f129c3f000a:

```sh
python3 source/predict.py --output-dir /your/output/directory
```

The default HBM input is our independent bandwidth result in
`data/bandwidth-calibration.json`; all other architecture inputs are in
`data/model-provenance.json`. The saved output includes both the kernel body
and a separate 2 µs launch estimate.

## Reproduce the GPU preparation conditions

Build with the recorded CUTLASS revision 954c8d7be60d730cc3f51e8f1ffe9850dce054d5
and CUDA 12.8:

```sh
CUTLASS_ROOT=/your/cutlass bash source/build.sh
CUDA_VISIBLE_DEVICES=YOUR_GPU CACHE_CONTROL_MODE=read_cg512 \
  CACHE_CONTROL_REPEATS=51 source/benchmark 16 26624 2752
```

The benchmark reports CUDA-event intervals. To reproduce the device-only
numbers on the page, capture an Nsight Systems CUDA trace, export SQLite,
then run `source/collect_trace.py` with that SQLite file and the launch
manifest. Do not substitute event intervals for kernel-body timings.
The full cache-state investigation documents the matched controls and counter
measurements. This page focuses on calculating the smaller case.
