# ATT40 — best full valid 2P1D result so far; strict windows still fail

Measured Alex run: [20260913_121454](http://43.156.43.133:31019/replay/runs/20260913_121454/report?view=overview&columns=overview). All **11,842 requests succeeded**, with zero failures, empty outputs or unadmitted requests. Full600s C05 load, output20, generator valid. No CPU stack or locals probes were used.

## Result

TTFT p50 / p90 / p99: **2.966963 / 4.146221 / 5.334008s**. All603 Alex trailing20s completion-window points were independently reconstructed. **20windows exceeded4s**, worst **4.531601s at t=573**, 394samples. Therefore the strict research target is not met. Failing point seconds are preserved in `evidence/ANALYSIS-PROVENANCE.json`.

The prior best full valid run ATT33 had p50/p99 3.773244/6.919942s and213/603 failing windows, worst6.115510s. ATT40 improves the observed whole-run percentiles and window count, but startup source and Prefill/routing incarnations differ; this is not an isolated randomized effect estimate. ATT34/35 remain generator-invalid diagnostic comparisons.

Generator heartbeat lag p99 **44.319547ms**, admission delay p99 **36.526530ms**, body-send delay p99 **42.835604ms**, zero connector waits. Original50ms/50ms/100ms thresholds are unchanged.

## Load, cache and late spike

Offered estimated input600,333,103; server input600,333,408; cached539,530,944; uncached60,802,464 tokens. Actual hit89.871884%, approximately60.033M input/6.080M uncached TPM over600s. Net finite-plan cache deficit798,080tokens. All42,621 exact full60s admission-window states passed recorded engineering bands: input59.4–60.6M, uncached5.7–6.3M. These are engineering bands, not an invented contract tolerance or physical per-second GPU throughput.

Store had47eviction passes and2,958,159,226,368cumulative evicted bytes; capacity remained1,300GiB. This is churn, not unique working-set size. At admission540–555s, extra finite-plan uncached work was112,576tokens and cohort p50was4.193s;555–570s p50was4.432s. Both Prefills showed greater queue time near the late spike.

Existing traces for16selected requests completing in the worst20s window versus8controls completing at60–80s show mean Prefill wait1.819323/0.479073s; forward1.090991/0.991769s; bootstrap0.791095/0.612128s; handoff0.728730/0.679028s. Decode wait0.000193/0.000232s. Selected requests are not input/cache matched (mean uncached3,337/10,190tokens) or randomized. Stages overlap and are not additive causal TTFT contributions. The evidence points toward Prefill queueing for the residual spike. The initial trace read failed because the local Feishu user token expired; normal refresh succeeded, then24request traces/1,296spans were recovered. No browser fallback or additional serving instrumentation was used.

Next experiment:12K Prefill chunks/max-prefill/matching graph with the same startup-budget source, C05 traffic, output20, affinity and Store settings. Preserve this10Kbaseline and rollback. No5.6M fallback is justified by this result alone.

## Source and validation

Same exact runtime as closed warmup-only ATT39: seven retained changes plus the opt-in startup logits-budget hook. Scheduler SHA256 `85bbce778a5683b013c54824e29eef2119fcde27e50c8954183f7e9fe00bf63d`; complete eight-candidate patch `48a16944ecb09fea4b2dca5d7e8520ca8c5821ad7f54a51981c2d1f8ef0e884c`. All source/image/container identities were rechecked at closure. No production merge or draft PR has been created; packaging remains deferred until2P1D is sorted out.

ATT39's six canonical and four affinity checks were explicitly inherited from the same incarnations, followed by fresh complete dataset/token/generator verification and a cache reset on both Prefills/all eight Decode DP ranks. Fresh warmup121122 completed400/400successes, valid lagp992.340717ms, cold TTFTp50/p9917.811329/23.931497s. This warmup is separate from the measured result. Binding-map state was not dumped; the preceding long pause exceeded the1800sidle TTL. KV resets do not clear that map.

No runaway backlog stop occurred. All115queuegauges were idle in two closure checks and all four collectors joined. Frontend had0ERROR events and68lower-tier removal warnings across warmup/measurement/drain; output20parser truncation warnings are separately retained. TPOT tails remain deferred: 37requests>40ms/25>80ms, 79windows>40ms p99. No full TPOT certification is claimed.

## Reproduction

Exact recipe: `chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`; source: `candidate/`, complete patch and reconstruction receipt under`preparation/`; original rollout/rollback: ATT39`rollout/INTENT.json`. ATT40 has no rollout mutation. Runtime identities and inherited checks: `runtime-bound.json`, `evidence/`. Warmup/measurement config, cache reset, terminal metrics, accounting, load audit and guards: `replay/`. Raw timing export: `../evidence/20260913_121454/`; reconstruction: `../evidence/latency-comparison-20260913_121454.json`; selected existing traces: `spike-traces/`; full600s stage comparison: `evidence/affinity-stage-cache-600s.json`. Raw prompts/logs/credentials are excluded from public reports.
