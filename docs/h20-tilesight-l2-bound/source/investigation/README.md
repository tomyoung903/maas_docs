# Follow-up reproduction

The rate correction comes from an independent instruction microbenchmark. It is not fitted to any GEMM time.

## CPU prediction

Use the TileSight development revision linked by the page. From this directory:

```bash
PYTHONPATH=/path/to/TileSight python3 predict.py --output-dir /tmp/h20-instruction-predictions
```

The script restores archived memory rates from `../../data/summary.json` and applies each Tensor rate only to its analysis. It does not edit the installed profile. The original HMMA model has312CTAs at4/SM; the WGMMA control has78CTAs at1/SM, confirmed by counters.

## Independent instruction calibration

On an idle H20, explicitly restrict CUDA_VISIBLE_DEVICES to the selected GPU. Do not run on a GPU occupied by another workload. CUDA12.8 was used for the measured build.

```bash
cd hmma-probe
NVCC_BIN=/usr/local/cuda-12.8/bin/nvcc bash build.sh
./probe --groups 1,2,4,8,16 --threads 128,256 --blocks-per-sm 1,2,4,8 --iterations 4096,8192 --repeats 7
```

The `probe.cu` supplied here is the actual CUDA12.8 source. The archived `remote-cuda12-probe.cu` is the same file. A local CUDA13 compilation removed only an obsolete device-clock metadata field; it was not used for the reported GPU timings. The CUDA12.8 SASS and instruction-count check are in `../../data/investigation/`.

The WGMMA probe is adapted from TileSight's supplied Hopper microbenchmark, with a fixed-nonzero correctness check added. Build `wgmma-probe/wgmma.cu` with `nvcc -O3 -DNDEBUG -arch=sm_90a`, then run with `--data nonzero --iters 20000 --repeat 11 --warmup 5`, varying `--blocks-per-sm` over1,2,4,8. Raw event timings, exact-output checks and clock samples are archived.

## Kernel controls

Build the variant subdirectories with the pinned CUTLASS checkout and CUDA12.8:

```bash
CUTLASS_ROOT=/path/to/cutlass NVCC_BIN=/usr/local/cuda-12.8/bin/nvcc PIPELINE_STAGES=3 bash build.sh
```

Use `CACHE_CONTROL_MODE=read_cg512` or `warm` and `CACHE_CONTROL_REPEATS=31` with `build/stages3/benchmark 64 9984 2048`. Keep cache preparation outside the timed interval. Match every kernel launch in an Nsight Systems device trace to `launches.csv`; use phase `measure` for the reported median. WGMMA uses the `cutlass::device_kernel` symbol; the original uses `cutlass::Kernel`.

The diagnostic phase-instrumented variant is not the original binary. Its timestamps are thread0 observations without added barriers. Counter profiles use separate application replay and must not replace primary device-trace durations. All aborted attempts remain excluded; no external workload was stopped.

The detailed source-order plan in the audit is exploratory, not the accepted rate correction. Its32.595µs result is not claimed as validated agreement.

For clean text diffs, the published SASS exports and instrumented CUTLASS header have trailing whitespace normalized. The original exports and measured sources remain in the experiment archives. The primary HMMA probe source is byte-identical to its recorded source checksum.
