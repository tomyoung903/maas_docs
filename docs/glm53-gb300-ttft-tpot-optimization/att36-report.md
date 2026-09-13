# ATT36 — 10K Prefill: backlog stop, all admitted requests drained

Measured Alex run: [20260913_100538](http://43.156.43.133:31019/replay/runs/20260913_100538/report?view=overview&columns=overview). Warmup:20260913_100118. **Interrupted negative trial: 4,227 successes, zero failures/empty outputs, 7,615 never admitted.** Last body upload t=213.803159s; last completion t=228.834466s. It is not a completed 600s test. The pre-existing backlog guard stopped admissions with frontend active283 and Prefill queue218 after active>=250 and queue>=120 sustained15s. Every admitted identity matches the candidate05 prefix.

## Result and measurement boundaries

Whole-run client TTFT p50/p90/p99: **8.341904 /16.658194 /18.039237s**. All228 Alex trailing20s completion-window points were independently reconstructed from raw timestamps. **151 windows exceeded4s p50; worst12.321726s at t=228 with382 samples.** The live last200-request median previously reached approximately14.3s; it is a different cohort and is not the acceptance chart.

Generator timing was valid: event-loop lag p99 **31.889159ms**, source admission p99 **32.313575ms**, body-send delay p99 **43.826945ms**, zero connector queue events. Existing50/50/100ms limits remain unchanged. A valid generator does not turn this interrupted, high-latency trial into a pass.

Actual input214,040,783, cached192,517,888, uncached21,522,895 tokens: **89.944489% cache hit**. Whole admitted-span boundary approximation:60.067M offered input and6.040M actual uncachedTPM. Net cache deficit versus finite plan150,272 tokens. Full60s rolling windows are audited only within the observed admission interval; no full600s workload qualification is claimed. Store counters cover measured baseline through closure, including drain and subsequent idle time.

## Exact change, initial state and verification

Only three Prefill arguments changed: chunk and max-prefill12288→10240, plus graph-size12288→10240. Two Prefill pods rolled; the other six pod/container identities stayed fixed. Same serving images/source, six optimizations plus producer-event wait, resources, two PP4 Prefills on132/151, one TP8/DP8/EP8 Decode on130+192, affinityTTL1800 and escape0, output20 and candidate05. P KV capacity9,252,096/rank, D3,135,616/rank, private Store1300GiB unchanged.

The original valid-ATT35 apply prerequisite is preserved, together with `preparation/DECISION-AMENDMENT.json`. Both isolated CPU controls closed before this candidate was applied. ATT33 remains a valid full-run reference; ATT34/35 are generator-invalid diagnostics. Original final acceptance gates were not relaxed.

Additional comparison factors: new Prefill incarnations/session placements, one status snapshot per15s instead of three, and an external OS sampler for the generator. The prior no-request gap exceeded1800s idleTTL; this is source-based expiration evidence, not a memory dump. Of4,227 matched admitted requests, only1,846 used the same logical Prefill node as ATT35. Actual Prefill IDs all changed; the distributed Decode ID stayed fixed. Completion records do not expose Decode DP rank. No isolated causal effect of chunk size is claimed.

Fresh six canonical retrieval/L3 checks and four affinity checks passed. Exact18,048-token L3 reads were verified on all four PP ranks in both directions, and actual10K graph batches appeared. This is bounded coverage, not comprehensive correctness. Fresh cache reset covered both Prefills and all eight DecodeDP ranks. Warmup400/400 succeeded; cold-cache TTFT p5017.230613s, p9922.090609s, generator lag p992.198295ms. Warmup values are separate from measured acceptance.

## Prefill imbalance evidence

P132 received2,273 admitted requests with12,024,515 uncached tokens; P151 received1,954 with9,498,380 uncached tokens. Mean client TTFT was6.543s versus10.924s. At nominal90–120s, PP0 observation counters showed mean forward0.977s versus1.622s and queue1.346s versus7.614s. These counters include readiness and are not matched additive TTFT spans.

In that same nominal30s interval, P132 logged166 batches and P151107; P151's107 were all full10K CUDA graph batches. Graph fallback therefore does not explain its slowdown. P151 had longer average cached context per batch and lower sampled GPU utilization. Its arriving uncached demand was lower, so assigning it more uncached work is not the direct explanation. Placement, context/batch shape, CPU/communication and runtime state remain investigation candidates.

Startup graph memory was identical between Prefills for corresponding ranks. Post-run process inspection inside each worker found its four scheduler processes and corresponding GPU allocations; the DCGM container's empty process query was a PID-namespace visibility limitation, not evidence of empty GPUs. Post-run inspection does not prove absence of transient interference during the test. No CPU affinity, resource or scheduling setting was changed.

The generator OS sampler captured2,135 samples from t=54.387 to267.787s, including drain/postprocessing. Cgroup quota-throttle counters did not increase during that coverage. Kernel schedstats were disabled; zero runqueue counters cannot exclude contention. No Python hooks or application mutations were used. Its exact child exited and the sampler was joined.

## Closure and retained artifacts

All115 queue gauges were idle in two closure checks, every bound identity/source hash matched, and all collectors/guards were joined. `replay/evidence/DRAINED.json` records acceptance false. Twelve lower-tier removal warnings and zero frontend ERROR events occurred in the complete watcher interval. TPOT remains deferred:13 requests above40ms,9 above80ms;22 chart windows above40ms p99. No new correctness or TPOT overlay was introduced.

Recipe and rollback: `chart/`, `preparation/`, `rollout/`. Exact runtime: `runtime-bound.json`, `evidence/runtime-attestation.json`. Raw timings and original checksum: `../evidence/20260913_100538/`; reconstructed chart: `../evidence/latency-comparison-20260913_100538-partial.json`. Request accounting and load: `replay/workload-analysis.json`, `rolling-load-cache-audit.json`. Diagnostics: `evidence/affinity-stage-cache-210s.json`, `first210s-batch-shapes.json`, `placement-prefix-summary.json`, `generator-os-audit.json`, `startup-memory-comparison.json`, and private node/process observations. Exact private request/session mappings remain local.

Current serving state after closure is idle10K. Next investigation: retain this configuration for a bounded diagnostic repeat, sample Prefill CPU stacks to distinguish scheduling/communication stalls from batch/context cost, and keep the unchanged final acceptance requirements. Profiling observations will be labeled diagnostic. A new source patch has not been prepared or merged.
