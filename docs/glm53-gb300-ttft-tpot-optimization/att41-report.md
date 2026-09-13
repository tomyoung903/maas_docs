# attempt41-two-prefill-12k-startup-budget — strict TTFT trial not accepted

Alex measured run: [20260913_125341](http://43.156.43.133:31019/replay/runs/20260913_125341/report?view=overview&columns=overview). Full600s C05 traffic, output20, 12288token Prefill chunks. All **11,842 requests succeeded**, zero failures/empty/unadmitted. Generator **valid**. Outcome reasons: 19/603TTFTwindows>=4s, one or more recorded load/cache engineering bands missed.

## Latency and generator

Whole-run TTFT P50/P75/P90/P99: **3.198143/3.685325/4.289379/5.594766s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All603Alex trailing20s completion-window points were independently reconstructed. **19/603windows reach or exceed4s**; worst **4.495855s at446.0s**, 374samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **39.882404ms**, admissionp99 **34.245920ms**, body-sendp99 **44.272663ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,416,128, uncached60,917,280tokens. Hit89.852759%; net finite-plan uncached excess912,896tokens. Full600s input/uncached TPM: 60.033341M/6.091728M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **False**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,957,911,444,992bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits

Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The same eight-candidate source is retained, including the opt-in startup logits-budget hook. Source, images, resources, L2/L3settings, strictaffinity1800/escape0, C05dataset/tokenprofile andoutput20 are preserved; exact render delta is in`preparation/PREPARED.json`. ChangingPrefillchunks also replacesPrefillincarnations/routingassignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Rejection sampling remains prepared for the later12GPU1P1D task; it is not enabled here.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_125058 completed400/400, generatorvalid, coldTTFTP50/P99 16.714087/21.680874s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. Persistentserving remainsretained. TPOTtailwork is deferred: 26requests>40ms/23>80ms; 40windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/` and`preparation/complete-eight-candidate-against-frozen.patch` preserve source; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_125341/`; latencyreconstruction:`../evidence/latency-comparison-20260913_125341.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt41-two-prefill-12k-startup-budget/`. Rawrequests/credentialsareexcludedfrompublicreports.
