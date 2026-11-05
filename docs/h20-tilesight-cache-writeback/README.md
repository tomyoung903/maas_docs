# H20 cache-state investigation

This page extends the memory-bound GEMM walkthrough. The small workload is
M=16, N=26,624, K=2,752, with FP16 inputs/output and FP32 accumulation.

The unchanged TileSight prediction is 41.063650671 µs. Controlled Nsight Systems
medians are 52.032 µs after write-based eviction and 42.080 µs after read-only
eviction. Each condition has 51 samples. These are device-only kernel durations;
cache preparation and the launch gap are outside the timed kernel interval.

The earlier archived write-based measurement was 52.128 µs. Its sample set is
not replaced by the new controlled reproduction.

## Source versions

- TileSight development revision: `6673bc3941d23572caad5d25473c9f129c3f000a`.
- CUTLASS revision: `954c8d7be60d730cc3f51e8f1ffe9850dce054d5`.
- CUDA 12.8, H20 `sm_90a`; `cp.async` / `mma.sync` instruction path.
- Independently measured HBM calibration: 3,860,654,536,000 bytes/s.

The published `data/prediction.json` is the unchanged full prediction snapshot.
The renderer checks its kernel-body time and all per-condition medians against
the saved device samples.

## Reproduce timing controls

Set `CUTLASS_ROOT` to the pinned checkout and optionally set `NVCC_BIN` to the
CUDA 12.8 compiler. Build without changing the GEMM template:

```sh
bash source/build.sh
```

After selecting an available H20 through `CUDA_VISIBLE_DEVICES`, run in a new
output directory because the benchmark writes `samples.csv` and `launches.csv`:

```sh
/path/to/source/cache_controls 16 26624 2752
CACHE_CONTROL_MATCHED_CARVEOUT=1 /path/to/source/cache_controls 16 26624 2752
/path/to/source/dirty_sweep 16 26624 2752
```

For the original shape, use `16 79872 8192`. The default is 51 samples per
condition, interleaved in shuffled order. `CACHE_CONTROL_REPEATS` changes the
sample count. `CACHE_CONTROL_MODE` selects one named condition.

The first benchmark contains the ten preparation modes in `data/measurements.json`.
The dirty sweep always uses a common read-only eviction, followed by optional
4/16/32/64/128 MiB read-modify-write prefixes. These prefix sizes are bytes
modified by preparation, not measured dirty cache residency.

The CUDA-event intervals printed by the binaries differ from the device-only
Nsight Systems durations used on the page. Preserve that distinction when
comparing a rerun. The source checks correctness against cuBLAS on a deterministic
input fixture, and validates the read-sweep checksum before and after all modes.

To obtain the device-only intervals, use a fresh output directory:

```sh
nsys profile --trace=cuda --sample=none --cpuctxsw=none --output=device \
  /path/to/source/cache_controls 16 26624 2752
nsys export --type=sqlite --output=device.sqlite device.nsys-rep
python /path/to/source/collect_trace.py --sqlite device.sqlite \
  --launches launches.csv --output collected
```

The collector matches the exact GEMM launch sequence in `launches.csv`; it does
not assume that every kernel in the trace is a timed GEMM. Use the same procedure
with the dirty-sweep binary. The collected CSV files are the inputs validated by
the page renderer.

## Data and limits

- `data/measurements.json`: summaries and shape metadata.
- `data/*_trace.csv`: all 2,397 measured device samples from five trace runs.
- `data/counters.json`: hardware-counter collection and interpretation.
- `data/counter-dram-pairs.csv`: three matched one-pass HBM counter comparisons.
- `data/counter-full-metrics.json`: the separate three-pass comparison of HBM,
  L2, Tensor, ALU, FMA, and load/store-unit activity.
- `data/prediction.json`: full unchanged TileSight output.
- `source/cache_controls.cu`: ten preparation controls.
- `source/dirty_sweep.cu`: write-size sweep.

The mechanism animation is schematic. The duration bars compare a model with
measured medians; they do not locate individual stalls or writebacks inside GEMM.
Read-only eviction replaces inputs with unrelated clean lines and does not make
the cache literally empty. Other workloads and initial memory states require
their own validation.

## Hardware-counter verification

Nsight Compute 2026.1.1 successfully collected the published data using a
temporary container granted `CAP_SYS_ADMIN`. The host's administrator-only
profiling policy remained enabled. A narrower `CAP_PERFMON` attempt was denied
on this installed driver/tool stack. Profiling used an existing CUDA image,
read-only tool/input mounts, and the selected GPU only.

Application replay used `--cache-control none` and `--clock-control none`.
With `CACHE_CONTROL_REPEATS=1`, the selected mode performs one correctness GEMM,
100 warmups, one priming GEMM, and one measured GEMM. The profiler filters
`cutlass::Kernel.*`, skips 102 matching launches, and collects the next one.
This preserves the application's preparation before each replayed measurement.

The one-pass comparisons request `dram__bytes_read.sum` and
`dram__bytes_write.sum`. The three-pass comparison also requests the L2,
Tensor, and arithmetic metrics named in `counter-full-metrics.json`.
The three independent one-pass pairs show 24.04–25.25 MB of extra HBM writes
after write-based eviction, with nearly unchanged HBM reads. The separate
full-metric pair shows unchanged SM-origin output writes and arithmetic counts.

Do not use timings printed under Nsight Compute as substitutes for the earlier
Nsight Systems measurements. Counter collection perturbs execution. Compare
traffic within a matched collection rather than pooling metric sets with
different replay-pass counts. The counters directly measure extra writes;
they do not identify each written address or allocate each microsecond of delay
to a specific transaction.
