# GLM-5.3 GB300 EAGLE 3-1-4 · six-arm intersection matrix

Every arm reports the same 1,907-position all-six intersection.
The two sampling cohorts contain different source requests; mode comparisons are within each cohort.
Observed online request mix: approximately 60% temperature 1.0 / top-p 0.95 and approximately 40% temperature 0.7 / top-p 0.7.

## temperature 0.7 · top-p 0.7

Requests in every arm: 1,907.

| Arm | Requests | Strict acceptance | Accept length incl. bonus |
|---|---:|---:|---:|
| Rejection sampling off | 1,907 | 77.3186% | 3.31956 |
| Stock rejection sampling | 1,907 | 76.6843% | 3.30053 |
| Top-p-aware rejection sampling | 1,907 | 77.9431% | 3.33829 |

- Stock rejection sampling minus off: -0.6343 pp.
- Top-p-aware minus stock rejection sampling: +1.2588 pp.
- Top-p-aware minus off: +0.6245 pp.

## temperature 1.0 · top-p 0.95

Requests in every arm: 1,907.

| Arm | Requests | Strict acceptance | Accept length incl. bonus |
|---|---:|---:|---:|
| Rejection sampling off | 1,907 | 64.5837% | 2.93751 |
| Stock rejection sampling | 1,907 | 71.3108% | 3.13932 |
| Top-p-aware rejection sampling | 1,907 | 71.6347% | 3.14904 |

- Stock rejection sampling minus off: +6.7271 pp.
- Top-p-aware minus stock rejection sampling: +0.3239 pp.
- Top-p-aware minus off: +7.0510 pp.
