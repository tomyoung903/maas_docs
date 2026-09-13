# attempt44-two-prefill-10k-timing-allocator — strict TTFT trial not accepted

Alex measured run: [20260913_143815](http://43.156.43.133:31019/replay/runs/20260913_143815/report?view=overview&columns=overview). Full600s C05 traffic, output20, 10240token Prefill chunks. All **11,842 requests succeeded**, zero failures/empty/unadmitted. Generator **valid**. Outcome reasons: instrumented diagnostic; uninstrumented confirmation required, 79/603TTFTwindows>=4s, one or more recorded load/cache engineering bands missed.

## Latency and generator

Whole-run TTFT P50/P75/P90/P99: **3.031778/3.695910/4.628039/7.101334s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All603Alex trailing20s completion-window points were independently reconstructed. **79/603windows reach or exceed4s**; worst **6.186856s at314.0s**, 375samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **43.525517ms**, admissionp99 **31.620801ms**, body-sendp99 **38.188156ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,329,984, uncached61,003,424tokens. Hit89.838409%; net finite-plan uncached excess999,040tokens. Full600s input/uncached TPM: 60.033341M/6.100342M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **False**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,958,463,762,176bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits

This arm adds the separately recorded opt-in allocator reporter and native device timer to the retained eight performance candidates. Native counter coverage and possible observation overhead are recorded under evidence/native-diagnostics-*. It is not an uninstrumented acceptance replay.

Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The same eight-candidate source is retained, including the opt-in startup logits-budget hook. Source, images, resources, L2/L3settings, strictaffinity1800/escape0, C05dataset/tokenprofile andoutput20 are preserved; exact render delta is in`preparation/PREPARED.json`. ChangingPrefillchunks also replacesPrefillincarnations/routingassignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Rejection sampling remains prepared for the later12GPU1P1D task; it is not enabled here.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_143422 completed400/400, generatorvalid, coldTTFTP50/P99 17.848080/23.356509s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. Persistentserving remainsretained. TPOTtailwork is deferred: 20requests>40ms/18>80ms; 20windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/` and`preparation/complete-eight-candidate-against-frozen.patch` preserve source; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_143815/`; latencyreconstruction:`../evidence/latency-comparison-20260913_143815.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt44-two-prefill-10k-timing-allocator/`. Rawrequests/credentialsareexcludedfrompublicreports.

## Native diagnostic findings

All eight Prefill ranks exposed forward-event counters and native PyTorch allocator statistics. Across the measured interval there were **five allocator retries and zero allocator OOMs**; warmup had fifteen retries separately. Retry increases fell between adjacent snapshots at approximately26–31s,37–42s,77–82s,210–215s and302–307s. These bounds locate observations, not allocation durations. Failing20s-window ranges were139–145s,308–343s,440–458s and497–513s. The worst range followed one retry, but later spikes had no new retries; retry elimination alone is not established as a solution.

Twenty-four retained request traces reproduce eight stage intervals per request. Sixteen requests selected across the worst completion window had mean Prefill waiting3.474s versus0.178s for eight controls completing60–80s. Prefill forward means were1.057/0.737s, bootstrap0.858/0.606s and handoff0.844/0.616s. Decode waiting remained approximately0.25ms and forward0.234/0.239s. These are selected, unmatched cohorts; durations overlap and are not additive causal contributions. Diagnostic source and new Prefill incarnations prevent interpreting ATT44-versus-ATT40 differences as observer overhead alone.

Full-span PP0 observation counters show queue means887/688ms onP132/P151 versus632/606ms inATT40. Forward/bootstrap/handoff means changed much less. Per-rank forward-event spans include stream/enqueue gaps; they are not pure kernel utilization. The15s GPU snapshots retain actual offsets, clocks, temperatures and power; sparse readings do not prove or exclude thermal/power throttling.

Evidence: `evidence/native-diagnostics-findings.json`, `native-diagnostics-600s.json`, `native-diagnostics-stage-summary.json`, `native-diagnostics-node-health.json`; trace cohort/queries/decomposition under `spike-traces/`. Feishu read credentials expired during trace acquisition; a single normal token refresh succeeded, followed by24/24trace matches. No credential values were recorded in public evidence. One analyzer invocation selected the older5921-request helper and failed before output; the existing11842-request arm helper completed unchanged, recorded in `evidence/ANALYZER-INVOCATION-CORRECTION.json`.

The MQA logits-buffer lifetime patch remains offline/prepared only. Its44CPU cases pass, but native stream/numerical/capture validation is pending. It has not been deployed and does not account for these results. No lower-load fallback or6Mcapacity ceiling is established.
