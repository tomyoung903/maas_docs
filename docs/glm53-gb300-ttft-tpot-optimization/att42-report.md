# attempt42-two-prefill-8k-startup-budget — strict TTFT trial not accepted

Alex measured run: [20260913_132716](http://43.156.43.133:31019/replay/runs/20260913_132716/report?view=overview&columns=overview). Full600s C05 traffic, output20, 8192token Prefill chunks. All **11,842 requests succeeded**, zero failures/empty/unadmitted. Generator **invalid**. Outcome reasons: load generator invalid under original thresholds, 32/603TTFTwindows>=4s.

## Latency and generator

Whole-run TTFT P50/P75/P90/P99: **2.933608/3.535343/4.149217/5.658676s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All603Alex trailing20s completion-window points were independently reconstructed. **32/603windows reach or exceed4s**; worst **4.385677s at557.0s**, 397samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **54.661163ms**, admissionp99 **33.708861ms**, body-sendp99 **41.625065ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,618,304, uncached60,715,104tokens. Hit89.886436%; net finite-plan uncached excess710,720tokens. Full600s input/uncached TPM: 60.033341M/6.071510M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **True**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,957,479,110,144bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits

Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The same eight-candidate source is retained, including the opt-in startup logits-budget hook. Source, images, resources, L2/L3settings, strictaffinity1800/escape0, C05dataset/tokenprofile andoutput20 are preserved; exact render delta is in`preparation/PREPARED.json`. ChangingPrefillchunks also replacesPrefillincarnations/routingassignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Rejection sampling remains prepared for the later12GPU1P1D task; it is not enabled here.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_132423 completed400/400, generatorvalid, coldTTFTP50/P99 18.460691/25.112313s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. Persistentserving remainsretained. TPOTtailwork is deferred: 31requests>40ms/26>80ms; 71windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/` and`preparation/complete-eight-candidate-against-frozen.patch` preserve source; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_132716/`; latencyreconstruction:`../evidence/latency-comparison-20260913_132716.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt42-two-prefill-8k-startup-budget/`. Rawrequests/credentialsareexcludedfrompublicreports.
