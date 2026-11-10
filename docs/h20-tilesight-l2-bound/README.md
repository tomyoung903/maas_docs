# H20: testing an L2-bound GEMM prediction

Fixed before measurement: M=64, N=9,984, K=2,048; FP16 A/B/C, FP32 accumulation; tile 16×128×64; three stages; four CTAs/SM; grid 4×78; 32 K steps. TileSight uses `cache="trace"` and `ii_mode="periodic_best"`. The prediction is 23.615784017822 µs excluding the separate 2 µs launch term.

Measured on gpu-h20-5, physical GPU 4, on 10 November 2026, Singapore time. The byte-identical archived CUTLASS kernel reports 128 threads, 64 registers/thread, 55,296 shared-memory bytes, and occupancy four CTAs/SM. No competing selected-GPU process was observed. Other GPUs were active; no exclusive node reservation is claimed.

## Results

- Primary: 51 Nsight Systems kernel intervals after read-only 512 MiB eviction. Median 34.368 µs, p10–p90 34.208–34.528 µs.
- Warm-input device median: 33.824 µs. Warm does not imply an all-hit cache.
- Unprofiled CUDA-event median after eviction: 38.464 µs, a different timing definition.
- Prediction error: −31.2855%. The model remains unchanged.
- All 638,976 outputs match cuBLAS exactly for the deterministic seed-17 multiples-of-1/8 inputs. No arbitrary-input bitwise-accuracy claim is made.

## Reproduce

Use TileSight commit `6673bc3941d23572caad5d25473c9f129c3f000a` and the local H20 profile. The saved `data/summary.json` records the actual hardware-rate inputs. Run CPU-only:

```sh
PYTHONPATH=/path/to/TileSight CUDA_VISIBLE_DEVICES='' \
  python3 source/predict.py --output-dir /path/to/prediction-output
```

Build with CUTLASS commit `954c8d7be60d730cc3f51e8f1ffe9850dce054d5` and CUDA 12.8:

```sh
CUTLASS_ROOT=/path/to/cutlass NVCC_BIN=/path/to/cuda-12.8/bin/nvcc bash source/build.sh
CUDA_VISIBLE_DEVICES=<available-device> CACHE_CONTROL_MODE=read_cg512 \
  CACHE_CONTROL_REPEATS=51 CACHE_CONTROL_MATCHED_CARVEOUT=0 source/benchmark 64 9984 2048
```

For device-only timing, run the same command under Nsight Systems 2025.6.3 with `profile --trace=cuda --sample=none --cpuctxsw=none -o device`, then export SQLite. Match CUTLASS kernel entries to `launches.csv`; only `phase=measure` belongs in the primary median. The samples, launch ledgers, observations and raw `.nsys-rep` files are included.

To recalculate this archive's timing summary, export `data/read_cg512.nsys-rep` to `data/read_cg512-nsys/device.sqlite`, and `data/warm.nsys-rep` to `data/warm-nsys/device.sqlite`, using `nsys export --type sqlite --output <sqlite-file> <report-file>`. Then run:

```sh
python3 source/analyze.py --input-dir . --output-dir rechecked
```

The analyzer also accepts the original `runs/<mode>-<kind>/` experiment layout and writes new output separately from saved evidence.

## Counters

Nsight Compute 2026.1.1 used application replay, `--cache-control none`, `--clock-control none`, launch skip 102 and count 1 filtered to the CUTLASS kernel. The broad cold run requested ten metrics and used six application replays. The smaller cold/warm pair requested the same four metrics. Keep their results separate.

Hardware counters show cache reuse, but do not establish L2 bandwidth saturation. NVIDIA's broad cold LTS throughput metric is 36.44%; this is distinct from FLOP utilization and useful-byte ratios. Exact requested metric values and raw reports are in `data/counters/`.

Counter access reused a temporary single-device profiling container with the verified capability and explicit GPU/driver bindings. Host driver policy stayed `RmProfilingAdminOnly: 1`. The first wrapper attempt rejected its own container process when its name appeared as `[No data]`. The second finished profiling successfully but hit a post-exit `docker top` race; its exit-zero archive was verified and exported offline. The two final traffic profiles completed normally. All created containers were removed; no host permission, power, or clock setting was changed.

The maintained webpage generator is `tools/h20_tilesight_l2_bound/build.py` in the MaaS Docs repository. `SHA256SUMS` hashes every published artifact. This report preserves the original prediction and measurements; it does not fit a new rate to close the gap.
