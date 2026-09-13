# ATT30 — 12K chunk-only 2P1D trial

The trial failed the latency and zero-error goals. It is an interrupted experiment, not a completed ten-minute result.

- Alex: http://43.156.43.133:31019/replay/runs/20260913_063354/report?view=overview&columns=overview
- Measured admission began 14:33:57.234 Singapore on 13 September 2026. Last request body was sent at 186.546644 seconds; last client completion was at 209.692875 seconds.
- 3,954 requests were admitted: 3,942 succeeded and 12 received HTTP 529. All outcomes are preserved; 9,515 planned requests were never admitted. No retries replaced failures.
- Every HTTP 529 joins to a frontend Prefill-overload rejection: eleven selected Prefill132, one selected Prefill151. There were no logged Decode bootstrap failures. The first-failure poller stopped new admissions at about 186.6 seconds. The predeclared sampled backlog guard had not reached its thresholds; it did not prevent the first rejection.

## Exact change and reproduction

Relative to ATT29, only both Prefill argument lists changed: chunk size and maximum Prefill tokens 8,192 → 12,288, and graph bucket 12,288 added to 512/1,024/2,048/4,096/8,192. Async depth 1, max-running 80, memory fraction 0.85, cache policies, all source overlays and all images remained fixed. Prefill132 and Prefill151 each use PP4/TP1 on four GPUs. Decode130/192 is one TP8/DP8/EP8 replica on eight GPUs, with 96 max-running per DP rank. The shared Store remains two 650 GiB clients.

The immutable ATT29 reference is `../expanded-four-node/two-prefill-one-decode/`. Current values, rendered manifests and exact before/after argument diff are under `preparation/`; rollout receipts and old identities are under `rollout/`. `runtime-bound.json` binds all eight actual pod/container/image identities. `replay/evidence/DRAINED.json` records final identity, source, Mooncake-version and idle checks. Six non-Prefill incarnations stayed unchanged across rollout. The existing Store192 restart count of one did not increase.

The original six optimization patches plus the producer CUDA-event fix are in `../candidates/optimized-async-kv-event/`; the frozen SGLang source is `/mnt/HPC/tom/experiments/glm53-optim-exp-1p1d/sources/sglang-6d08e28b0c0691899973e3f11bf01fdbdf192a63`. Complete Helm input is retained in `chart/` and `preparation/values.json`. No repository source or image was changed for ATT30.

Workload: unchanged candidate04, 13,469 measured requests / 600 seconds, target 60M input and 6M uncached tokens/minute, output cap 20, max concurrency 1,024, timeout 120 seconds, source scheduling, session header enabled, no synthetic unique prefix. Dataset `dataset-dfa320022c5b1e8c171a2227`, profile `profile-0f6d63bca1c499991a2a2073`. Exact configs and generator/token-store hash checks are in `replay/`.

## Correctness and warmup

`correctness-01/` records a pre-probe reset rejection with zero submitted test requests. A concurrent readiness canary made Prefill151 busy; the Dynamo handler rejected the reset before flushing. Bounded retries were added only for this exact pre-flush busy response, with identity rechecks and all responses retained.

`correctness-02/` passed six requests: cold/shared/cold trios in opposite Prefill directions, using Decode DP0 on130 and DP4 on192. Exact final identifiers, DONE, input/cache counts, physical Decode rank counters and cross-Prefill 18,048-token storage reuse matched. Actual 12K graph replay was observed on all eight Prefill PP ranks. This is bounded correctness evidence, not a general accuracy claim.

After a new scoped cache reset, warmup `20260913_063114` completed 400/400 with no errors or empty successful output. Duration128.347s; TTFT p50/p99 17.081/23.280s; TPOT p99 15.736ms; hit30.7551%. Warmup is reported separately and is not a latency pass.

## Measured outcomes, including drain

| Metric | ATT30 observed result |
|---|---:|
| Successful-request TTFT p50 / p99 | 6.458 / 23.364 s |
| Worst Alex20s completion-window TTFT p50 | 22.219 s at210s;324 samples |
| Alex points with TTFT p50 above4s |147 of209 reconstructed points |
| Whole-run TPOT p99 |19.396 ms |
| Worst Alex20s TPOT p99 |30.110 ms at97s;384 samples |
| Requests with TPOT above40ms / above80ms |5 /0 |
| Successful input / cached / uncached tokens |185,778,129 /165,287,424 /20,490,705 |
| Successful token-weighted hit rate |88.9703% |
| Extra uncached tokens versus finite plan, successful requests |1,890,176 |
| Estimated offered input TPM over admission span |60.038M |
| Known successful uncached TPM over admission span |6.591M |

The twelve rejected requests have no server input/cache usage. Their estimated input is included in offered load; their unknown cache usage is not silently set to zero. The approximate admission-span rates use whole-request boundary accounting, not a 600-second denominator. Alex's own excluded-final-request offered estimate is60.032M TPM. All209 saved latency points were independently reconstructed from raw timing. Short output and stream coalescing remain limitations; 1,573 successful requests have zero observed first-to-last generation span.

Generator validity passed: request-body scheduling delay p99 30.293ms, admission delay p99 24.367ms, loop lag p99 22.069ms, and no connector queue events. Peak active client requests422.

## What this rules in and leaves open

Queue growth preceded Store eviction. The45–60s arrival cohort already had TTFT p50 4.547s with only3,072 extra uncached tokens versus plan. First Store eviction is bounded by samples78.484–83.485s. The first successful request with at least1,024 missing cached tokens was admitted95.040s. Later cache loss worsened uncached load: first-minute uncached6.005M; second-minute6.522M; third-minute successful uncached7.233M with six rejected requests separately retained.

Store counters are cumulative across resets. ATT30 deltas are11 eviction passes,1,566,680 physical keys and690,285,782,016 bytes evicted. Final occupancy1,222,127,212,032 bytes is not itself an eviction counter. Actual Store eviction operates on ordinary object leases; the offline prefix-preserving leaf-LRU model remains optimistic. A separate post-ATT29 sample found all eight physical objects present for254 actual pages, so widespread partial-page eviction has not been established. A prepared-token-derived key probe matched no keys even for positive controls; its encoding/tokenization correspondence remains unresolved and cannot prove cache loss.

Compared with8K,12K increased early bootstrap and final-handoff means from roughly0.5–0.7s to0.8–1.1s. The stage comparison preserves labels and uses counter observations, not matched request cohorts; it is not an additive TTFT decomposition. Better partial TPOT and worse latency do not establish a full-run benefit.

Candidate04 also changes workload mix relative to twice the best1P1D workload:13,469 versus11,842 requests (+13.739%), mean input44,561 versus50,710 tokens, and1,254 versus768 sessions. A CPU-only candidate05 is being selected to control request rate while preserving real prompts and numeric/cache/diversity requirements. It has not been registered or launched. Matching request rate alone will not establish matching session working sets or length distributions.

## Evidence locations

- `replay/partial-analysis.json`: all request identities, failed/successful denominators, arrival cohorts and cache deficits.
- `replay/evidence/frontend-error-events.json`: sanitized failure events joined to all twelve client errors.
- `replay/evidence/eviction-timeline.json` and `store-counter-deltas.json`: scrape-aligned cache evidence.
- `../expanded-four-node/two-prefill-stage-comparison.json`: label-preserving30s stage deltas forATT29/30.
- `../expanded-four-node/dataset/workload-mix-comparison.json`: exact request-length/uncached-length/QPS comparison.
- `../evidence/20260913_063354/`: full timing/ITL/token timestamps, summary, timeseries, metadata and raw-file checksum.
- `../evidence/latency-comparison-20260913_063354-partial.json`: reconstructed209 Alex chart points.
- `replay/metrics/`, `node-samples.jsonl`, `runtime-health.jsonl`, and `replay/evidence/*-live.log`: preserved samplers. Raw logs may contain request payloads; do not publish them.

All115 serving queue gauges were zero in two final samples. All collectors stopped cleanly; all eight incarnations and source hashes remained unchanged during measurement. ATT28 remains the best completed1P1D run. The2P1D objective and full TTFT/TPOT/zero-error acceptance remain open.
