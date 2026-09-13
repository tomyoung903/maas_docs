# ATT35 — unchanged12K repeat; generator invalid again

Measured Alex run: [20260913_090354](http://43.156.43.133:31019/replay/runs/20260913_090354/report?view=overview&columns=overview). Warmup:20260913_090045. All11,842 measured requests succeeded, zero failures or empty outputs, with the complete600s schedule. **Final state: invalid_load_generator.** Event-loop lag p99 was **51.507188ms**, above the existing50ms limit. Admission p99 was37.205620ms, body-upload delay p9946.740758ms, and connector queue events zero. Those separate timing checks passed. The existing generator criterion remains; no accepted performance claim is made.

## Observed result

Whole TTFT p50/p90/p99: **3.369539 /4.546461 /5.658888s**. All602 Alex trailing20s chart points were independently reconstructed from raw completion timestamps. **60 windows exceeded4s p50**, with worst **4.492971s at t=324**,383 samples. ATT34 had56/603 failing windows and worst4.571117s, but was also generator-invalid. The two12K runs provide consistent diagnostic evidence of the service-time/queue tradeoff; neither passes TTFT acceptance or generator validation.

Actual input600,333,408, cached539,564,928, uncached60,768,480 tokens: **89.877545% hit**, approximately6.077M uncachedTPM. Net deficit versus the finite plan was764,096 tokens. Last body upload was t=599.962038s, last completion t=602.881305s. Every request identity matched candidate05; server/local input differed by305 tokens overall.

All42,621 boundary/interior states of full60s admission windows passed the recorded engineering demand bands. Offered input ranged59,735,225–60,302,200 tokens; actual input59,735,263–60,302,229; actual uncached5,935,560–6,276,722. The bands are ±1% input and ±5% uncached around60M/6M, not a substitute for the invalid generator criterion. Values group eventual server outcomes by request-body upload time, rather than measuring instantaneous physical computation.

## Exact unchanged runtime and retained routing state

No runtime configuration, serving source, image, resource, placement or generator validation limit changed from ATT34. All eight pod/container incarnations stayed fixed. Both Prefills remained PP4/TP1, chunk/max-prefill12288, matching breakable graphs, async depth1, max-running80, with the six optimizations and producer-event wait. One TP8/DP8/EP8 Decode spanned130+192. Frontend affinityTTL1800s and projected-load escape0 remained. Store remained two650GiB clients. Candidate05, output20,400-request warmup and11,842-request600s measurement were unchanged.

**Fresh KV reset did not clear frontend session bindings.** Original session IDs are retained by the replay client, and this repeat occurred inside the1800s idle TTL. The exact frontend and worker incarnations remained. Structured native logs bridged all11,842 client IDs to actual worker choices: **every request used the same Prefill and distributed Decode worker as in ATT34**;6,006 usedP151 and5,836 usedP132. The completion record identifies the distributed Decode worker, not its selected DP rank. This is a repeat with retained session placement, not a new-session routing replication. See `evidence/RETAINED-SESSION-STATE.json` and `retained-session-routing-11842.json`.

Six canonical and four affinity checks were explicitly inherited from ATT34's identical runtime, with source/identity closure reverified; no fresh correctness coverage is claimed. Fresh generator/payload/token attestation passed. A new scoped cache reset verified all eight DecodeDP ranks and both Prefills before warmup. The separate warmup completed400/400 without failures; its cold-cache TTFT p50 was18.452325s and p9923.917936s. These warmup values are preserved separately from measured acceptance.

## Queue/cache evidence and boundaries

The first360s PP0 counters closely repeat ATT34. P132/P151 mean forward was1.089/1.066s, bootstrap0.815/0.815s, handoff0.829/0.820s and queue0.673/0.542s. These are observation-time counter means, including readiness; stages are not additive matched-request TTFT spans. Full600s counters and actual scrape offsets are in `evidence/affinity-stage-cache-600s.json`.

Paired client/frontend TTFT joins cover all11,842 requests. In the worst window, client p50 was4.492971s and frontend p504.429890s; median paired duration difference11.852ms. Different boundary definitions prevent interpreting this as a network-only span. Nevertheless, the frontend's own timing still shows a greater-than4s median in the hot cohort, keeping Prefill service and queueing central to the TTFT investigation.

Store recorded47 eviction passes,6,696,721 evicted objects and2,958,534,517,248 cumulative evicted bytes from measured baseline through terminal idle. Allocated bytes837,775,471,104→1,204,916,825,088; capacity1,395,864,371,200 unchanged. Cumulative eviction counts churn. There were53 absent-block lower-tier removal warnings and no frontend ERROR events in the entire saved watcher interval.

TPOT remains deferred: whole p9919.010742ms, worst20s p99130.615214ms;26 requests above40ms,21 above80ms,44 chart windows above40ms p99. No standalone TPOT profiler or additional correctness-research overlay was introduced.

## Closure, artifacts and next decision

All115 engine/frontend queue gauges were idle in two checks. All eight identities and expected per-role source hashes matched after the run. Every collector and guard was stopped and joined. `replay/evidence/DRAINED.json` records acceptance false; `tool-sessions.json` has no active sessions.

Complete recipe: `chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `preparation/PREPARED.json`. No Helm apply occurred; `rollout/UNCHANGED.json` records that fact. Raw timing exports/checksums: `../evidence/20260913_090354/` and `../evidence/20260913_090045/`. Reconstructed chart: `../evidence/latency-comparison-20260913_090354.json`. All-request accounting and rolling demand: `replay/workload-analysis.json`, `rolling-load-cache-audit.json`. Source/identity proof: `runtime-bound.json`, `replay/evidence/DRAINED.json`. Private logs, metrics and node samples remain under `replay/`.

**ATT36's10K control is prepared but held.** Its before/after render, exact three-argument Prefill diff and rollback command are saved; application requires a completed valid baseline. Two consecutive generator-invalid runs make generator event-loop delay a current measurement blocker. Investigate that delay while keeping the12K serving runtime fixed, then resume TTFT iteration. Do not reinterpret a successful request stream as a valid benchmark.
