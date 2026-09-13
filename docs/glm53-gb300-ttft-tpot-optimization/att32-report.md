# ATT32: session affinity improved early locality but failed routing

Closed negative on 2026-09-13, Singapore time. This was a short interrupted experiment, not a ten-minute performance pass. The best completed 1P1D result remains ATT28.

## Workload and configuration

- Measured Alex run: [20260913_073337](http://43.156.43.133:31019/replay/runs/20260913_073337/report?view=overview&columns=overview), task `bench-75d997a302b46e9f`.
- Warmup: `20260913_072854`, 400 successful requests, no failures, followed by an independently verified idle interval.
- Candidate05 is unchanged from ATT31: 11,842 measured requests over 600 seconds, about 60M input and 6M modeled uncached TPM, approximately 90% cache reuse, maximum output 20 tokens. Same real payloads, IDs, schedule and prepared token profile. Alex sends `Session-Id`; it adds no artificial cache salt.
- Dataset `dataset-ff27e5775a3fafe07c306868`, profile `profile-4af517c7667ceb975392f966`, trace `/var/lib/replay/subsets/tom-capacity-v4-2p-matched-rate-60m-6m-20260913`.
- Two four-GPU Prefills on 132 and 151, PP4/TP1, 8,192-token chunks, pipeline depth one. One eight-GPU Decode across 130 and 192, TP8/DP8, 96 request slots per DP partition. Shared Store remains two 650GiB clients on 130/192.
- The only runtime change from ATT31 was frontend `--router-session-affinity-ttl-secs 1800`. The seven worker/Store pod identities, all images, source overlays, capacities and cache policies were unchanged. The pre-existing projected-load escape threshold remained 8,000ms.
- Affinity influences both Prefill and Decode routing. Admission control and external backlog/failure guards remained enabled.

Exact Helm values, complete renders, render hashes, reversible commands and scope checks are in `preparation/`; actual pod/container/image and source attestations are in `runtime-bound.json` and `evidence/`. No image was built and no SGLang source was changed for ATT32.

## Correctness before measurement

Six canonical retrieval requests passed: cold, cross-Prefill shared-cache hit and second cold requests in both directions. Exact answers, input counts and cache counts matched; all eight Prefill graph ranks replayed the expected 8K graphs. Four additional affinity probes passed: after seeding a session on P132/Decode DP0 or P151/DP4, a disjoint-prefix request without routing overrides stayed on that same binding. All four answers were correct. Changing Session-Id did not salt the tested synthetic KV prefixes.

The new frontend initially had no lazily initialized per-model queue series. The first correctness attempt sent zero requests; a separately recorded, bounded initialization request established those series. Missing metrics were never treated as zero. Startup-log rotation and one-time activation messages required explicitly checked inheritance from the same unchanged worker identities; failed setup attempts and corrected provenance checks remain preserved.

## Measured outcome

| Measure | Result |
|---|---:|
| Admitted / successful / failed | 970 / 956 / 14 |
| Never admitted | 10,872 |
| Last body sent / last completion | 48.626937 / 51.389825 s |
| Successful TTFT p50 / p90 / p99 | 2.267595 / 2.957702 / 3.444180 s |
| Worst Alex trailing 20s TTFT p50 | 2.573309 s, at 52s; 372 samples |
| Reconstructed chart points / points above 4s | 51 / 0 |
| Successful whole / worst 20s TPOT p99 | 19.396554 / 20.061851 ms |
| Individual successful requests above 40 / 80ms TPOT | 0 / 0 |
| Successful input / cached / uncached tokens | 47,990,466 / 43,190,336 / 4,800,130 |
| Successful cache hit / net deficit against finite plan | 89.997742% / 960 tokens |

All 14 failures were HTTP 400 with the same native error: `session session is bound to worker 3602676117442465, not 4600655023660740`. Those IDs map to bound P151 and selected P132. The failures belong to 14 separate sessions, begin at 41.610948s and end at 48.626937s. No preceding measured request in those sessions was still running at admission; one failed session had no earlier measured request, so warmup history must also be considered. This is not evidence of a first-request concurrency race.

The client-failure guard stopped only this run's admissions and drained its outstanding client requests. Failed requests have unknown server input/cache usage; the successful-request latency and hit-rate figures exclude those failures. They therefore cannot establish a full-load or zero-error pass. No capacity-overload rejection was observed. The Store recorded no eviction pass during this short measured interval and subsequent drain, so this trial does not test sustained physical retention pressure.

## Locality comparison before the failures

The same-label PP0 observation counters show less lower-tier cache work and shorter Prefill queues than ATT31. In approximately the first 30 seconds, combined host/shared-cache hit tokens fell from 908,928 to 196,736. In the next approximately ten seconds they were 2,302,592 versus 121,472. Corresponding mean queue times on P132/P151 were 1,070/1,564ms in ATT31 versus 521/452ms with affinity.

These counter cohorts use actual scrape offsets, include readiness traffic and are not matched request cohorts or an additive TTFT decomposition. Comparisons after the first error are affected by failed requests and the admission stop. `evidence/stage-cache-comparison.json` retains all counts, sums, intervals and offsets.

## Routing conflict and cleanup

The frozen Dynamo source provides a concrete candidate explanation. `lib/kv-router/src/scheduling/selector.rs` can drop a worker pin when modeled remaining Prefill time exceeds `prefill_overload_threshold_ms` and another worker is projected to become free sooner. `lib/llm/src/session_affinity/coordinator.rs`, in `AffinityAcquire::into_stream`, rejects a selected worker that differs from a bound session; its error deliberately uses the placeholder `session`. The router calls that validation after dispatching the selected worker stream.

That combination explains the observed error shape and orphaned Prefill work, but exact compiled native Rust source provenance is incomplete and debug pin-escape events were not enabled. Treat the explanation as a strong hypothesis pending the controlled threshold-zero trial. The frozen files and SHA256 values are retained in `evidence/affinity-policy-audit/`. The native constructors accept affinity 1800s with a zero projected-load escape threshold. A failed constructor probe that placed the setting on the wrong config type is also retained; it changed no runtime state.

After Alex closed, P132 retained 14 bootstrap entries. Every failed client request was joined through the worker trace ID to exactly one PP0 bootstrap timeout at 300 seconds. The entries cleared around 15:39:23–15:39:30 Singapore. Two complete metric checks subsequently verified all 115 queue gauges idle; all eight original identities and source hashes remained unchanged. No worker restart or cache reset was required for recovery. An occasional single running/inflight readiness request is separately visible and was not counted as a failed client request.

## Reproduction and next control

Attempt root: `/mnt/HPC/tom/pd-latency-followup-20260913/attempt32-two-prefill-session-affinity`.

- `preparation/PREPARED.json`, `trial-values.json`, renders and hashes: exact settings and rollback.
- `runtime-bound.json`, `evidence/runtime-attestation.json`, `native-affinity-active.json`: actual runtime identities and native flag.
- `correctness-02/`, `affinity-correctness/`: synthetic payloads, SSE outputs, route-counter evidence and closure receipts; no real source prompts are published.
- `replay/launch.py`, both config/start/final files, `attest_generator.py`: exact load launch and dataset/generator checks.
- `replay/workload-analysis.json`, `measured-events-slim.jsonl`, `evidence/frontend-error-events.json`, `bootstrap-timeout-correspondence.json`: all admitted requests and failure accounting.
- Parent `evidence/20260913_073337/`: raw timing export, summary, chart data and raw-event SHA256. `replay/analyze_latency.py 20260913_073337 --allow-partial` independently reconstructs Alex windows.
- `replay/metrics/`, metric/node/runtime observations and eight live logs: retained runtime and resource evidence.
- `replay/evidence/DRAINED.json`, terminal idle receipt and `tool-sessions.json`: recovery, source verification and collector closure.
- Parent `worker/{prepare,apply,watch,bind}_two_prefill_session_affinity.py`: the scoped frontend-only rollout helpers.

ATT33 keeps affinity1800 and changes only `--router-prefill-overload-threshold-ms` from 8000 to 0. This disables both pinned-worker and scored-cache projected-load escape; hard admission limits and external guards remain. It may expose load imbalance and is not presumed to pass. The same fresh cache reset, 400-request warmup, candidate05 ten-minute load and exact latency/failure accounting are required.
