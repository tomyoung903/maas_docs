# Independent HMMA calibration review

The independent probe supports an empirical **95–96 TFLOP/s rate for the tested FP16-to-FP32 `mma.sync.m16n8k16` path** on this H20. Using the upstream generic 139.22 TFLOP/s for that path is too optimistic. This explains an important modeling error, but it does not fully explain the GEMM duration.

This review used local artifacts only. It did not run a GPU, modify a probe, or select a rate by fitting GEMM timings. Clear-writing guidance follows the `asd-ste100` skill.

## Measurement and accounting

The probe uses volatile `mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32` with register operands. One warp instruction performs `2 × 16 × 8 × 16 = 4,096 FLOPs`. Its total FLOP count is:

`grid_blocks × (threads / 32) × accumulator_groups × 8 × iterations × 4,096`.

There are no global or shared operand loads inside the repeated loop. Every accumulator is retained and checked exactly after execution. CUDA events include the final stores and kernel overhead; no duration is subtracted. Therefore, this measures a favorable arithmetic path, not the complete GEMM pipeline.

All 72 executed configurations pass correctness and report zero local-memory allocation. Eight configurations exceeding their calculated single-wave occupancy capacity are explicitly skipped. The grid's requested blocks per SM describe average work supply; the probe does not force CTA placement.

## Robustness of the plateau

Each configuration has seven timing samples and three warmups. The following ranges include both loop lengths and the indicated warp supply:

| Independent accumulator groups per warp | All configurations, TFLOP/s | Configurations supplying at least 16 warps per SM, TFLOP/s |
|---:|---:|---:|
| 1 | 88.069–95.780 | 94.281–95.780 |
| 2 | 93.953–95.804 | 95.405–95.804 |
| 4 | 89.073–95.499 | 95.306–95.499 |
| 8 | 92.333–95.667 | 95.545–95.667 |
| 16 | 94.053–95.750 | 95.691–95.750 |

The maximum, **95.804007744 TFLOP/s**, is a configuration's seven-sample median, not its fastest individual sample. That configuration uses two accumulator groups, 256 threads, eight blocks per SM in the grid, and 8,192 outer iterations. Its median duration is 27,974.400 µs; its minimum-to-maximum spread is 1.856 µs, or 0.0066%.

The baseline-like configuration—four accumulator groups, 128 threads, four blocks per SM—reaches **95.343970147 TFLOP/s**, only 0.48% below the maximum. It matches warp and accumulator supply, not the GEMM's complete instruction mix or register allocation.

Across all 36 configuration pairs, doubling the loop length from 4,096 to 8,192 changes the rate by only 0.006–0.569%, with a median change of 0.040%. This is strong evidence that fixed event, launch, and final-store costs do not explain the large difference from 139.22 TFLOP/s. Low-warp-supply cases run slower, as expected when instruction latency is less hidden.

All 55 clock samples with at least 90% GPU utilization report 1,980 MHz SM and 2,619 MHz memory clocks. Temperature stays at 39–40°C. The separate WGMMA probe also records 1,980 MHz active SM clocks and reports configuration medians of 142.206, 142.493, 142.567, and 142.650 TFLOP/s. A gross clock mismatch does not explain the observed instruction-path difference.

## Relation to the GEMM counters

The actual CUTLASS kernel uses `HMMA.16816.F32`. Of its 1,115 sampled math-pipeline-throttle events, 1,097 occur at HMMA instructions: 98.39%. This identifies the instruction family whose admission is frequently delayed. The independent probe now supplies the missing throughput measurement for that family.

This combination supports a path-specific rate correction. It does not establish that 98.39% of elapsed time is spent on HMMA, or that the same percentage of the prediction error has been explained. Stall samples from overlapping warps cannot be added as wall-clock time. The zero excessive shared-memory wavefront count also argues against shared-memory bank conflicts as the main explanation.

The independent WGMMA result shows that the generic rate is plausible for a different instruction path. The repository does not establish the original provenance of 139.22, so it must not be called a proven upstream WGMMA calibration.

## What the correction establishes

Using 95.804 TFLOP/s as the instruction-path rate changes the unchanged five-operation model from **23.616 µs to 28.401 µs** for M64 N9984 K2048. The corresponding repeated cold measurement is **34.240 µs**, leaving **5.839 µs, or 17.05%, underprediction**. The model's limiting resource changes from L2 service to Tensor arithmetic.

The generic rate is 45.3% higher than the measured rate: `139.22 / 95.804 = 1.453`. Substituting the measured rate therefore increases the arithmetic-only service time by 45.3%. This is not a causal percentage of the end-to-end error. The original 34.368 µs measurement and the newer 34.240 µs rerun must remain separately identified.

The WGMMA implementation's measured 24.576 µs versus its matched 19.584 µs model confirms a remaining problem after changing the implementation. That control also changes the tile geometry, input traffic, pipeline, and CTA arrangement. Its speedup cannot be assigned entirely to one instruction-family difference.

**95.804 is a reasonable empirical ceiling for this tested path and environment.** Choosing the fastest stable configuration avoids using a poorly supplied probe to exaggerate the discrepancy. It is still optimistic for predicting a mixed GEMM kernel: using a higher service rate produces a shorter prediction. It is not a universal H20 HMMA specification or a conservative upper bound on kernel duration.

The remaining gap requires modeling instruction issue, shared-to-register reads, synchronization, finite pipeline fill/drain, and implementation details. The current evidence does not assign a unique duration to each cause. Keep the original upstream result and the independently calibrated result visible. Do not replace all H20 Tensor Core rates with this one value.

## Evidence and completed instruction check

Paths below are relative to this investigation directory, `outputs/h20-l2-gap-investigation-20261110`:

- `probe-runs/hmma-independent/000.log`: all configuration summaries, correctness, resource metadata, and rates.
- `probe-runs/hmma-independent/probe-samples.csv`: all individual event samples.
- `probe-runs/hmma-independent/clocks.csv`, `intent.json`, `cleanup.json`: device identity, clocks, and run lifecycle.
- `probe-runs/wgmma-independent/000.log` through `003.log` and `clocks.csv`: independent WGMMA control.
- `pc-summary.json`, `baseline-source.csv`: HMMA throttle locations and shared-wavefront evidence.
- `hmma-probe/remote-cuda12-probe.cu`, `build.log`, `cuda12-sass.txt`, `cuda12-sass-check.json`, and `SHA256SUMS`: measured build's source, compiler log, disassembly, instruction counts, and recorded checksums.
- `model/MEASURED-HMMA-RATE.md`: unchanged-plan predictions using the independent rate.

The measured CUDA 12.8 build's SASS is now archived and checked. All ten kernel templates contain exactly `8 × groups` `HMMA.16816.F32` instructions per outer loop: 8, 16, 32, 64, or 128 instructions for 1, 2, 4, 8, or 16 accumulator groups. The compiler log reports no spills. The archived remote source matches its recorded SHA-256 checksum. The instruction and FLOP accounting therefore use the measured build's disassembly, without relying on the earlier local CUDA 13 compile.

Archive check completed after review: the measured CUDA 12.8 executable and source were pulled into `hmma-probe/probe` and `probe.cu`. Both now pass `sha256sum -c SHA256SUMS`. The earlier local CUDA 13 executable and source are retained under distinct `local-cuda13-` filenames. The public evidence includes source, disassembly and build provenance; the executable remains in the experiment archive.
