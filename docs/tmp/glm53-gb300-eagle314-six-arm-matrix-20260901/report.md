# GLM-5.3 GB300 EAGLE 3-1-4 · six-arm paired matrix

Primary display: 1,907 common cohort-local ordinal positions in every arm.
Cross-cohort ordinal equality is not source-request identity; true request pairing remains within each three-arm cohort.

## temperature 0.7 · top-p 0.7

All-six common valid positions: 1,907.

| Arm | Durable | Retained | Shared valid | Strict acceptance | Accept length incl. bonus |
|---|---:|---:|---:|---:|---:|
| Rejection sampling off | 1,999 | 1,997 | 1,907 | 77.3186% | 3.31956 |
| Stock rejection sampling | 1,995 | 1,995 | 1,907 | 76.6843% | 3.30053 |
| Top-p-aware rejection sampling | 1,992 | 1,991 | 1,907 | 77.9431% | 3.33829 |

- Stock rejection sampling minus off: -0.6343 pp.
- Top-p-aware minus stock rejection sampling: +1.2588 pp.
- Top-p-aware minus off: +0.6245 pp.

## temperature 1.0 · top-p 0.95

All-six common valid positions: 1,907.

| Arm | Durable | Retained | Shared valid | Strict acceptance | Accept length incl. bonus |
|---|---:|---:|---:|---:|---:|
| Rejection sampling off | 1,993 | 1,986 | 1,907 | 64.5837% | 2.93751 |
| Stock rejection sampling | 1,993 | 1,993 | 1,907 | 71.3108% | 3.13932 |
| Top-p-aware rejection sampling | 1,990 | 1,982 | 1,907 | 71.6347% | 3.14904 |

- Stock rejection sampling minus off: +6.7271 pp.
- Top-p-aware minus stock rejection sampling: +0.3239 pp.
- Top-p-aware minus off: +7.0510 pp.
