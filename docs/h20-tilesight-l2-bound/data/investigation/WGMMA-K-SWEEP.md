# WGMMA K sweep: body prediction and residual

M64 N9984, tile64×128×64, TMA, WGMMA, FP16 inputs/output, FP32 accumulation, 3 shared stages, 256 threads.
78 CTAs spread one per SM. Parent verified the K2048 launch distribution with hardware counters.
All other model inputs are unchanged. Launch overhead is excluded from prediction and device-only measurement.
139.22 TF/s is the inherited rate;142.650 TF/s is the independent probe rate supplied by the parent, not fitted to GEMM.

| K | Rate TF/s | Tensor-only lower bound µs | Model body µs | Cold device µs | Cold residual µs | Warm residual µs |
|---:|---:|---:|---:|---:|---:|---:|
| 512 | 139.220 | 4.700 | 5.484 | 10.752 | 5.268 | 4.372 |
| 512 | 142.650 | 4.587 | 5.371 | 10.752 | 5.381 | 4.485 |
| 1024 | 139.220 | 9.400 | 10.184 | 15.360 | 5.176 | 4.248 |
| 1024 | 142.650 | 9.174 | 9.958 | 15.360 | 5.402 | 4.474 |
| 2048 | 139.220 | 18.799 | 19.584 | 24.576 | 4.992 | 4.288 |
| 2048 | 142.650 | 18.347 | 19.132 | 24.576 | 5.444 | 4.740 |
| 4096 | 139.220 | 37.599 | 38.383 | 43.136 | 4.753 | 4.721 |
| 4096 | 142.650 | 36.695 | 37.479 | 43.136 | 5.657 | 5.625 |

The tensor-only column is FLOPs / independently specified throughput. It excludes copies, synchronization, epilogue, and launch/dispatch costs, so it is not the full expected runtime.
The approximately constant WGMMA residual is evidence for an unmodeled fixed-cost component in this range. It is not proof of a unique mechanism and is not a calibrated offset.
The earlier HMMA family-rate correction left a residual that increased with K. The WGMMA implementation changes instruction family, CTA tile, request traffic, and residency together, so the different residual cannot be assigned exclusively to one change.
Do not add an empirically chosen constant to claim complete agreement. A fixed-latency model would require independent component evidence and prospective validation.
