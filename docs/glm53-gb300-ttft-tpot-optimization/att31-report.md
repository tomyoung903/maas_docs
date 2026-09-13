# ATT31: matching request rate did not stop Prefill queue growth

Closed negative partial trial, 13 September 2026. [Measured Alex report](http://43.156.43.133:31019/replay/runs/20260913_070704/report?view=overview&columns=overview); separate warmup20260913_070424. No full ten-minute acceptance is claimed.

## Configuration and workload control

Serving values exactly match ATT29: two independent4GPU Prefill replicas on132/151, each PP4/TP1/DP1 with8K chunks and graphs, depth1, max-running80; one distributed8GPU Decode on130/192, TP8/DP8/EP8. Both650GiB private Store clients and all images/source overlays remained fixed. ATT30 used12K chunks; reverting those chunks makes ATT29 the serving-matched reference. Only the two Prefill pods were replaced for this restoration; six other pod incarnations were unchanged. At trial closure all eight bound identities and source hashes were unchanged from ATT31's start.

Candidate05 controls the request rate at11,842 measured requests/600s, exactly twice ATT28's5,921, instead of candidate04's13,469. Mean input50,695.246 tokens is close to ATT28's50,710.221. The new selection contains600,333,103 prepared measured input tokens and60,004,079 modeled uncached tokens, approximately60M/6MTPM and90% reuse. It retains original real source bodies, unique source IDs, required ancestors,18s session spacing and20-output-token runtime cap. The400-request warmup is separate. There are1,324 measured sessions versus twice ATT28's384=768; matching request count does not match session diversity, length distribution or cache working set.

CPU-only Prepare20260913_065056 registered dataset`dataset-ff27e5775a3fafe07c306868`, profile`profile-4af517c7667ceb975392f966`. All12,242 warmup/measured token sequences were independently hash-matched to the prepared source; every original payload frame and deployed-loader identity was checked. The candidate SHA256 is`93eade32d9d6243c4e73e5aedeb362ea5543372ef543a9100478fd3bac306fa3`. Its63,904 numeric rolling-boundary checks passed the retained engineering tolerances, as did long-prefix diversity and the stated optimistic finite-cache scenarios. These do not guarantee runtime cache behavior or exact frontend/prepared-token correspondence for every real prompt.

## Correctness, warmup and stop

Six cold/shared/cold retrieval checks passed across both Prefill directions and Decode DP0/DP4 on both physical nodes. Each shared case independently recovered18,048 storage-hit tokens on all four receiving PP ranks. Actual8K graph replay was verified on all eight Prefill ranks, followed by115 idle queue gauges. A read-only master-admin key probe found all eight physical objects for all282 complete pages in each of two known synthetic fixtures. Normal page hashing matched; bigram and drop-first-token variants did not. This resolves synthetic-fixture correspondence only; the historical real-request missing-key probe remains inconclusive.

Fresh scoped reset flushed all eight Decode ranks, then both Prefills. Warmup completed400/400 without errors or empty outputs in133.053s; TTFTp50/p99=19.792/27.027s, TPOTp99=15.438ms. Warmup drained before measurement.

The predeclared backlog guard stopped admissions after active requests remained at least250 and the combined Prefill queue at least120 for15s. At stop it observed328 active requests,262 queued in Prefill and at most37 active/preallocation/transfer-stage requests in any Decode DP partition. This was below the96-per-partition limit. No frontend overload rejection or bootstrap failure was observed. All2,968 admitted requests completed successfully;8,874 were never admitted. Last body send149.955s, last completion170.387s. All115 gauges were idle twice, collectors joined, source checks passed. The shorter run is a failed experiment, not reduced-load success.

## Measured results

| Metric | Partial observation |
|---|---|
| TTFT whole p50 / p90 / p99 |5.294 /15.015 /18.525s|
| Worst Alex20s TTFTp50 |16.477s at169s;120 of170 points above4s|
| TPOT whole / worst Alex20s p99 |20.287 /22.711ms|
| Individual TPOT above40 /80ms |4 /1 requests|
| Success / failure / empty |2,968 /0 /0|
| Input / cached / uncached tokens |150,127,248 /133,910,592 /16,216,656|
| Actual token-weighted hit |89.1981%|
| Net cache deficit versus finite plan |1,215,232 tokens|
| Approximate admission-span offered input / actual uncached TPM |60.069M /6.489M|

All170 saved Alex trailing20s completion-window points were reconstructed from raw timestamps, including startup and drain. The generator remained valid; exact delay and queue statistics are retained in`replay/workload-analysis.json`. These partial TPOT results cannot certify ten-minute reliability. Client stream coalescing is retained rather than interpreted as physical per-token engine speed.

The first arrival minute carried60.237M input/6.022M uncached tokens,90.0028% hit and TTFTp502.996s. Minute2 carried59.948M/6.579M,89.0257% hit and p506.884s. The final29.955s cohort had87.9243% hit and p5015.024s. Every admitted ID matches the exact candidate prefix; eventual completions are assigned to their original arrival cohorts.

## What the control establishes

Queue growth again preceded Store eviction. The30–45s arrival cohort already had TTFTp504.064s with only704 net extra uncached tokens;45–60s reached4.442s with1,536 extra. First Store eviction is bounded by78.829–83.837s. The first request losing at least1,024 planned cached tokens was admitted83.319s. Store counters increased by eight eviction passes,1,139,816 physical keys and503,375,130,624 bytes; prior trials' counters were subtracted.

Same-label PP0 stage counters show mean queue time in30–60s of1.560/1.813s on ATT31's two Prefills, versus0.141s in ATT28. Forward means were0.881/0.840s versus0.727s. These stage observations are different cohorts, include readiness probes and are not an additive TTFT decomposition.

There is also a concrete cache-tier difference. In approximately the first minute, ATT28's sampled Prefill processed2.821M new tokens and25.400M device-hit tokens, with zero host/storage-hit tokens. ATT31's Prefills processed2.753M/2.811M new tokens each, but additionally fetched a combined8.285M cached tokens from host memory or shared storage. The similar uncached rate therefore does not mean equal work on the cache-transfer path. ATT31 retained many more sessions, and both local host caches approached capacity. This supports testing cache locality and transfer overhead; it does not yet isolate their causal contribution.

The frontend logged215 lower-tier event warnings (`Failed to find block`). The inspected frozen source raises this on removal of an unknown block; these warnings alone do not establish failed insertion or causal cache loss. Comparable raw frontend logs for ATT28 were not retained here, so its warning count is unknown. The ordinary Store's object/lease eviction differs from the offline prefix-preserving model; the earlier ancestor-lease hypothesis remains unimplemented.

## Reproduction and next comparison

Private root:`/mnt/HPC/tom/pd-latency-followup-20260913/attempt31-two-prefill-matched-rate`. Exact recipe:`preparation/trial-values.json`, `preparation/runtime-render.yaml`, private chart and`runtime-bound.json`. `control.py`, `correctness.py`, `close_correctness.py`, `replay/launch.py`, collectors, conservative backlog/failure guards and analyzers retain execution details. Source closure:`replay/evidence/DRAINED.json`; raw timing exports:`../evidence/20260913_070704/`. Dataset provenance, all-frame audits and token verification:`../expanded-four-node/dataset/candidate05-matched-request-rate/`.

ATT31 introduced no SGLang source patch. Its diagnostic monitor was improved to recognize structured frontend overload messages immediately without treating user prompt text as fatal logs. No GPUs outside130/132/151/192 or Windows Chrome session were used.

The installed native frontend exposes`RouterConfig(...session_affinity_ttl_secs=None)`, and the private chart supports`frontend.router.sessionAffinityTtlSecs`. Next candidate: enable bounded session affinity with the same candidate05 bodies/schedule and all worker/Store settings fixed, verifying actual Prefill/Decode routing first. This tests locality without changing the workload. A frontend restart and fresh scoped caches are required; no ATT32 change had been applied when this report was written. Affinity may trade load balance for reuse and also affects Decode placement; that must be measured, not presumed beneficial.
