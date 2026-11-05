# H20 memory-bound GEMM

This bundle accompanies the worked page. The archived measurement uses
M=16, N=79,872, K=8,192, FP16 inputs/output and FP32 accumulation.
The prediction is 305.990850063 µs; the cold-prepared device median is 363.264 µs.

## Source and versions

- TileSight: https://github.com/tomyoung903/TileSight/tree/71c51b223230b4bc13cfcaf3cb1ca25363e6ffb9
- CUTLASS: https://github.com/NVIDIA/cutlass/tree/954c8d7be60d730cc3f51e8f1ffe9850dce054d5
- CUDA 12.8, an NVIDIA H20, and Nsight Systems for device-only durations.

`source/benchmark.cu` is the original benchmark. `source/build.sh` requires
`CUTLASS_ROOT` to point to the pinned checkout. The accompanying include file
is retained from the original build. Set `NVCC_BIN` if nvcc is not on PATH.

On an available H20 selected with CUDA_VISIBLE_DEVICES:

```sh
bash source/build.sh
source/benchmark 16 79872 8192 --metadata-only
source/benchmark 16 79872 8192
```

The metadata query should report 128 threads, 55,296 shared-memory bytes,
64 registers/thread, and 4 active blocks/SM. Do not run against an occupied GPU.
The benchmark initializes inputs, checks against cuBLAS, performs 100 warmups,
then measures repeated-input and cold-prepared samples and CUDA Graph replay.
Its flush kernel touches 512 MiB outside the timed GEMM interval.
CUDA-event results printed by the benchmark are not the same timing definition
as the separate Nsight Systems device-duration samples saved in data/samples.csv.

## CPU prediction

Install the pinned TileSight checkout and its dependencies according to its
README, then run in a copy of this bundle (the script writes new snapshots):

```sh
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python source/predict.py
```

The script uses data/cases.json and data/kernel-metadata.json. It explicitly
sets occupancy from the metadata and uses H20().set_to_microbench(), cache=fast,
ii_mode=periodic_best. No constants were fitted to the measured runtime.

The public predictor preserves the original modeling code but writes beside
the bundled data and omits the original machine's absolute source path. The
build script requires explicit dependency paths instead of private defaults.
The original provenance snapshot likewise omits only that absolute path.
Full model, plan, operation costs, measurement JSON, and samples are included.
Machine inventory and raw profiler containers are not included in this public bundle.

## Timing reconstruction

Per-CTA time is 128 × 1.187411846690 + 0.078658218841 + 0.587479729924
+ 0.043717744765 + 0.296852961672 = 152.995425031509 µs.
624 CTAs / (78 SMs × 4 resident CTAs/SM) gives two waves, or 305.990850063017 µs.
The separate 2 µs launch term is excluded from the device-only comparison.

This is an aggregate tile model. It does not itemize all shared-to-register
instructions, epilogue exchanges, address work, barriers or fixed latencies.
The measured gap remains 15.77%; useful-byte bandwidth is not a hardware-counter
measurement of physical traffic.
