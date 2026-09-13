# ATT33 — complete doubled-traffic run; TTFT windows still fail

Measured Alex run: [20260913_075613](http://43.156.43.133:31019/replay/runs/20260913_075613/report?view=overview&columns=overview). Warmup: 20260913_075245. Both completed. All 11,842 measured requests and all 400 warmup requests succeeded; no empty output, HTTP rejection, bootstrap failure, or guard stop. The measured load generator was valid. Every one of 115 engine/frontend queue gauges drained, all eight pod/container identities stayed fixed, and runtime source hashes matched after the run.

## Primary result

The 600-second schedule admitted its last request at 599.965239 seconds and finished at 603.591151 seconds. Actual server input was 600,333,408 tokens, cached input 539,642,176, uncached input 60,691,232: 89.890412% token-weighted cache hit. Alex offered-input rate was 60.032940M TPM. Actual uncached traffic was approximately 6.069M TPM. All admitted identities matched the exact candidate05 schedule. The finite-plan net cache deficit was 686,848 tokens; server/local input differed by 305 tokens across the entire run.

Whole-run TTFT p50/p90/p99: 3.773244 / 5.246590 / 6.919942 seconds. Every Alex chart point was independently reconstructed from raw completion timestamps. Of 603 valid trailing-20-second windows, 213 exceeded four-second TTFT p50. Worst: 6.115510 seconds at t=508, with 395 samples. This is a complete zero-error result, but it does not pass the primary TTFT acceptance criterion.

## Change and reproduction

Only the frontend changed from ATT32: `--router-prefill-overload-threshold-ms 8000` became `0`, keeping session-affinity TTL 1800 seconds. Zero disables native projected-load escape, including pinned-worker fallback; hard active-token/block admission and external backlog guards remained. All seven other pod/container incarnations, images, worker sources, caches and candidate05 traffic remained fixed. Native PID flags were independently checked; the native extension SHA256 remained `940d698e115b88236ed1266f3f8b78daf0471c1159a26ccf0fe83a4264f87d3f`.

Topology: independent PP4/TP1 Prefills on 132 and 151; one TP8/DP8/EP8 Decode spanning 130 and 192. Prefill chunks/max-prefill-tokens 8192, asynchronous PP depth 1, existing producer-event wait overlay retained. Store: two 650GiB clients, one private master; total 1300GiB. Dataset `dataset-ff27e5775a3fafe07c306868`, token profile `profile-4af517c7667ceb975392f966`; 400-request warmup, exact 11,842-request/600-second measured schedule, maximum output 20.

Exact Helm values/render and before/after diff: `preparation/`. Runtime identities, capacities and source hashes: `runtime-bound.json`, `evidence/runtime-attestation.json`, `replay/evidence/DRAINED.json`. Workload/config/clock: `replay/`, with `warmup-config.json`, `measured-config.json`, `evidence/measured-clock.json`. Frozen overlay code is retained in `chart/files/`; chart templates show each mounted file and startup wrapper. No image was rebuilt for ATT33.

Six canonical cold/shared/cold retrieval checks and four affinity routing checks passed before the fresh cache reset and replay. Every shared retrieval verified all four PP ranks. These bounded checks remain useful regressions, not a general correctness guarantee.

## Queue and cache evidence

The TTFT-hot trace cohort contains 16 requests completing in t=(488,508]. Its mean Prefill waiting span was 3.647376 seconds versus 0.571241 seconds for eight control requests completing in t=(60,80]. Mean Prefill forward was 0.836480 versus 0.776351 seconds; bootstrap 0.666617 versus 0.515957; handoff 0.660209 versus 0.559194. These are selected cohorts, not randomized causal attribution. Decode transfer-wait overlaps Prefill work and must not be added to these Prefill stages.

`evidence/affinity-stage-cache-600s.json` retains PP0 observation-time stage and GPU/host/shared-cache counters for both Prefills. Earlier stopped arms are clipped before their last admission. These counters include readiness probes and are not exact per-request cohort decompositions. Session affinity substantially reduced lower-tier movement compared with ATT31, while finite cache misses and intermittent Prefill queues remained.

From the measured baseline through the terminal idle scrape, Store recorded 47 successful eviction passes, 6,694,784 evicted objects and 2,957,666,580,480 evicted bytes. Allocated bytes rose from 837,775,471,104 to 1,206,494,366,976. Cumulative evicted bytes include churn and are not the unique working-set size. Capacity stayed 1,395,864,371,200 bytes. See `replay/evidence/store-counter-deltas.json` and retained five-second scrapes.

## Deferred TPOT finding and current priority

Whole-run TPOT p99 was 19.615613ms; worst chart-window p99 was 152.274142ms at t=480. Forty requests exceeded 40ms, 31 exceeded 80ms, and 100 chart windows exceeded 40ms p99. The 24 worst sampled requests averaged 0.257569 seconds in Decode forward and 2.270165 seconds from Decode scheduler completion to root-request completion. This separates GPU/scheduler work from a later delay but does not identify its exact cause. Spans cross processes and sometimes nodes; the shared service name does not establish a single clock. Control end-gap differences were millisecond scale. No CPU profiler or new tracing overlay was applied.

At 16:22 Singapore, Tom explicitly deprioritized standalone TPOT and further KV-correctness research unless they block the primary 2P1D goal. Preserve these findings and existing correctness safeguards; focus subsequent experiments on full-load TTFT, request success, Prefill queueing and L3 behavior. Next proposed control is 12K Prefill chunks with the same strict affinity and candidate05 schedule.

## Evidence locations

- Raw timing exports and checksums: `../evidence/20260913_075613/` and `../evidence/20260913_075245/`.
- Exact chart reconstruction: `../evidence/latency-comparison-20260913_075613.json`.
- Every request's load/cache accounting: `replay/measured-events-slim.jsonl`, `replay/workload-analysis.json`.
- Trace queries, 48 exact request-to-trace joins and 2,592 spans: `spike-traces/`; decomposition and post-scheduler gaps retained separately.
- Runtime logs, node samples, metrics, guards and closure: `replay/`. Collectors were stopped and joined after terminal idle; `tool-sessions.json` records them.
- Initial summary export failed because Alex had not finalized its files; retry exported both complete runs. Expired monitoring-document authentication was refreshed before the successful read-only trace lookup. Neither incident changed serving configuration or request results.
