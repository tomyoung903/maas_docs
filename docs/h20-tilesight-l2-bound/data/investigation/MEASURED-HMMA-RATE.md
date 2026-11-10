# Independently measured HMMA-rate correction

HMMA rate: 95.804007744 TF/s from the parent-coordinated independent register-resident instruction probe.
The largest independently observed sustained rate is used as the ceiling. It was not fitted to GEMM timing.
Applied through the per-analysis `tensor.fp16.mma` explicit capacity. Stored H20 profile unchanged.
The original five-operation plan, cache trace, memory rates, and device-only timing definition are unchanged.

| K | Tensor-only bound µs | Five-operation prediction µs | Cold measured µs | Remaining gap µs | Underprediction |
|---:|---:|---:|---:|---:|---:|
| 64 | 0.854 | 1.936 | 3.712 | 1.776 | 47.83% |
| 128 | 1.707 | 2.790 | 4.768 | 1.978 | 41.48% |
| 256 | 3.415 | 4.498 | 6.656 | 2.158 | 32.43% |
| 512 | 6.830 | 7.912 | 10.592 | 2.680 | 25.30% |
| 1024 | 13.659 | 14.742 | 18.496 | 3.754 | 20.30% |
| 1536 | 20.489 | 21.572 | 26.368 | 4.796 | 18.19% |
| 2048 | 27.319 | 28.401 | 34.240 | 5.839 | 17.05% |
| 2560 | 34.148 | 35.231 | 42.080 | 6.849 | 16.28% |

The selected II is now Tensor Core service, rather than L2 read service.
This is a justified rate correction, but the remaining error is real. No fixed overhead or schedule parameter has been fitted to close it.
All these GEMM K cases are validation cases relative to the independent instruction microbenchmark, though they were already observed during this investigation; this is not a blind prospective validation.

The separately saved exploratory SASS-tail plan is not a validated correction: it aggregates four independent warps, models register overwrite release at full compute completion, and may not exhaust the schedule search.
