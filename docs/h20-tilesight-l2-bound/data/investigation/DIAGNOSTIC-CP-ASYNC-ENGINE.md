# Diagnostic copy-engine interpretation

L2 stays at 8.123448629 TB/s. HMMA stays at the independent 95.804007744 TFLOP/s.
`GenericOracle` divides an explicit engine capacity by residency only (`generic_oracle.py:476–482`). Therefore the whole-device effective path rate is divided by 78 before being passed through `Context.engine_throughput_bytes_per_s`.
The probe combines cp.async, waits, barriers, and checksum work. Its rate is an effective path proxy; it is not a measured isolated-engine peak. These are diagnostic predictions, not accepted calibration or a demonstrated bound on all workloads.

| Probe | Aggregate path TB/s | Per-SM input GB/s | Prediction µs | Remaining to 34.368 µs |
|---|---:|---:|---:|---:|
| 32MiB_combined_path | 7.906417530 | 101.364327308 | 28.420843 | 5.947157 |
| 16MiB_combined_path | 8.025505437 | 102.891095346 | 28.410050 | 5.957950 |

Adding this proxy as a separate cp.async service constraint does not remove the residual gap. It must not be interpreted as independent accounting of the waits and barriers already present in the calibration loop.
