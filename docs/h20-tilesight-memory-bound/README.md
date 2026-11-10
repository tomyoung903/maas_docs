# H20 memory-bound GEMM with measured bandwidth

The workload is M=16, N=79,872, K=8,192, with FP16 inputs/output and FP32 accumulation.
The CPU prediction is **341.045735879 µs**, using **3.860654536 TB/s** from an independent memory microbenchmark.
The original cold-prepared device median is **363.264 µs** (prediction 6.1163% low).
The original repeated-input median is **353.504 µs** (prediction 3.5242% low).
The GEMM was not rerun on the GPU for this update. Its original samples are preserved.

## Versions and scope

- TileSight: https://github.com/tomyoung903/TileSight/tree/71c51b223230b4bc13cfcaf3cb1ca25363e6ffb9
- CUTLASS: https://github.com/NVIDIA/cutlass/tree/954c8d7be60d730cc3f51e8f1ffe9850dce054d5
- Memory benchmark source: upstream TileSight commit `75428c41b7a1127497151a3db4316a1223d342cf`, unchanged.
- CUDA 12.8, NVIDIA H20, Nsight Systems device durations for the GEMM comparison.

The sole hardware-profile change for this rerun is `arch.ddr_bandwidth`.
`ddr_max_util` remains 1.0. The tile plan, residency, other rates and measurement samples remain unchanged.
The profile applies one aggregate HBM rate to reads and writes, so the output-store estimate changes too.
The measured read-path rate is a provisional device-specific calibration, not a universal rate for every access pattern.
No value was fitted to the GEMM runtime.

## Reproduce the CPU prediction

Install the pinned TileSight checkout and its dependencies, then run from a copy of this bundle:

```sh
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python source/predict.py
```

Results are written to `data/rerun`, leaving the archived snapshots intact.
Use `--output-dir PATH` to select another destination. The default rate comes from `data/bandwidth-calibration.json`.
To reproduce the upstream-profile and 8 GiB sensitivity runs:

```sh
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 python source/predict.py --hbm-bps 4305000000000 --output-dir data/rerun-upstream
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 python source/predict.py --hbm-bps 3789633832000 --output-dir data/rerun-8gib
```

The script builds the same five-operation plan and explicitly sets residency from `data/kernel-metadata.json`.
It uses `cache=fast` and `ii_mode=periodic_best`. Provenance records the loaded TileSight commit and profile values.
`data/bandwidth-comparison.json` contains all four comparisons, including the earlier nominal-board-rate sensitivity.
`data/upstream` preserves the original 4.305 TB/s prediction and plan.

## Independent bandwidth measurement

`data/bandwidth-run01.csv` contains 80 samples: four access methods, four block counts (78/156/312/624), five samples each.
`data/bandwidth-run02.csv` contains 60 samples: the same four methods at 156/312/624 blocks, five samples each.
The first run uses a 1 GiB allocation and seed 1729; the second uses 8 GiB and seed 1730.
Both exceed the 60 MiB L2 capacity. No clocks or power limits were modified.

The selected rate is the **median of five cp_async samples at 312 blocks in run 1**, the highest cp_async configuration median in that run.
It was selected before rerunning the GEMM prediction. The 8 GiB rate is a sensitivity check, even though it gives a closer prediction.
The samples and selection rule are recorded in `data/bandwidth-calibration.json`.

To compile the same unchanged benchmark on a compatible CUDA installation:

```sh
nvcc -O3 -std=c++17 -lineinfo -Xptxas=-v -gencode=arch=compute_90,code=sm_90 source/dram_sweep.cu -o dram_sweep
```

With an available H20 selected through `CUDA_VISIBLE_DEVICES`:

```sh
./dram_sweep --bytes 1073741824 --iters 1024 --guard-kb 0 --repeats 5 --blocks 78,156,312,624 --methods read_cg,write_cs,copy_cg_cs,cp_async --seed 1729
./dram_sweep --bytes 8589934592 --iters 1024 --guard-kb 0 --repeats 5 --blocks 156,312,624 --methods read_cg,write_cs,copy_cg_cs,cp_async --seed 1730
```

Bandwidth is requested bytes divided by CUDA-event device time, in decimal GB/s. Divide by 1,000 for TB/s.
Copy counts both reads and writes; cp_async counts global-to-shared bytes.
All 140 samples passed the benchmark's three-location checks. These are sampled checks, not exhaustive validation.

## Original GEMM measurement

`source/benchmark.cu` is the original CUTLASS benchmark. Set `CUTLASS_ROOT` to the pinned checkout and `NVCC_BIN` if needed:

```sh
bash source/build.sh
source/benchmark 16 79872 8192 --metadata-only
source/benchmark 16 79872 8192
```

The compiled kernel reports 128 threads, 55,296 shared-memory bytes, 64 registers/thread and four active blocks/SM.
The benchmark initializes inputs, checks against cuBLAS, performs 100 warmups, then measures repeated-input and cold-prepared samples and CUDA Graph replay.
Its separate cache-flush kernel touches 512 MiB outside the timed GEMM interval.
CUDA-event output is a different timing definition from the Nsight Systems device samples in `data/kernel-times.csv`.

## Timing reconstruction

The selected HBM rate changes the B-load interval to 1.324078068196 µs and the output store to 0.331019517049 µs.
Per CTA:

`128 × 1.324078068196 + 0.078658218841 + 0.587479729924 + 0.043717744765 + 0.331019517049 = 170.522867939700 µs`.

There are `624 / (78 × 4) = 2` full modeled waves, giving **341.045735879399 µs**.
The separate 2 µs launch term is excluded from the device-duration comparison.
The renderer rebuilds the overlap timeline from the saved solver witness and verifies this arithmetic.

The remaining 22.218 µs cold-prepared gap is unresolved. Access concurrency, cache state, unmodeled instructions and synchronization can contribute.
This result improves the comparison; it does not isolate each physical cause or establish accuracy for other workloads.

## Interactive L2 reuse explorer

The `#l2-reuse` section evaluates every access in the saved plan with TileSight's full trace cache model. It uses 60 MiB L2, 78 SMs, four resident CTAs per SM, and the two 312-CTA modeled waves. This is a CPU-only model calculation, not a new GPU measurement.

The display wraps the logical 1 × 624 output grid into 24 columns. Moving the K slider changes the A/B slice, while the predicted hit pattern is the same for all 128 K steps. A misses at output columns 0 and 312, then hits at the remaining 622 columns. Every B request is a first access. Across the entire plan, A's average L2-hit probability is 99.679487%; B's is 0%.

Full tracing assigns 512 KiB of HBM reads to A, including the second wave's reload, and 1.21875 GiB to B. The archived timing uses the original sampled `cache="fast"` result, which assigned zero HBM reads to A. The explorer does not silently change that historical prediction or its measurement comparison.

`data/l2-reuse-model.json` records the plan hash, TileSight commit, cache size, and full-trace results. `assets/l2-reuse.html` is a portable export retaining the visualization's sandbox and content security policy. Editable sources and reproduction commands are in `tools/h20_tilesight_memory_bound/l2-reuse/` in the MaaS Docs repository.
