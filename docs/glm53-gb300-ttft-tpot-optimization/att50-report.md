# attempt50-two-prefill-9k-compressed-logits — strict TTFT trial not accepted

Alex measured run: [20260913_180611](http://43.156.43.133:31019/replay/runs/20260913_180611/report?view=overview&columns=overview). Full600s C05 traffic, output20, 9216token Prefill chunks. All **11,842 requests succeeded**, zero failures/empty/unadmitted. Generator **valid**. Outcome reasons: 2/603TTFTwindows>=4s, one or more recorded load/cache engineering bands missed.

## Latency and generator

Whole-run TTFT P50/P75/P90/P99: **2.838442/3.434316/4.077913/5.518384s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All603Alex trailing20s completion-window points were independently reconstructed. **2/603windows reach or exceed4s**; worst **4.011806s at437.0s**, 374samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **35.292635ms**, admissionp99 **29.269145ms**, body-sendp99 **36.757174ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,173,376, uncached61,160,032tokens. Hit89.812322%; net finite-plan uncached excess1,155,648tokens. Full600s input/uncached TPM: 60.033341M/6.116003M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **False**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,958,400,104,192bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits



Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The recipe contains 10 performance candidates, including the opt-in startup logits-budget hook. Recorded delta: Only Prefill chunk8192to9216,max-prefill-tokens8192to9216,andadd9216graphshape. TwoPrefillpodsroll; sixotherpod/containeridentitiesfixed. Allsources/images/resources/traffic unchanged. Exact source and render checks are in`preparation/PREPARED.json`. Prefill replacement changes incarnations/routing assignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Rejection sampling remains prepared for the later12GPU1P1D task; it is not enabled here.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_180201 completed400/400, generatorvalid, coldTTFTP50/P99 17.335421/22.508929s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. Persistentserving remainsretained. TPOTtailwork is deferred: 29requests>40ms/26>80ms; 45windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/`, any `lifetime-candidate/` and`preparation/complete-ten-candidate-against-frozen.patch` preserve source and native qualification evidence; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_180611/`; latencyreconstruction:`../evidence/latency-comparison-20260913_180611.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt50-two-prefill-9k-compressed-logits/`. Rawrequests/credentialsareexcludedfrompublicreports.

## Interpretation and next decision

This is the smallest observed strict-window miss count among the retained full generator-valid2P1D trials: only elapsed247s (4.008330s,384samples) and437s (4.011806s,374samples) fail. It still fails Tom's strict<4s target. The load audit also finds432/42,621 overlapping uncached states above6.3M, maximum6.331259M; none below5.7M. These are correlated boundary states, not432independent minutes. All input states pass. ATT47 remains the best reference satisfying both generator and recorded load bands. This result does not justify relaxing any threshold.

At420–450s, PP0 observed queue means were1.203s onP132 and1.605s onP151, versus0.408/0.390s at60–90s. Bootstrap means were0.639/0.662s, forward0.887/0.904s and finalhandoff0.698/0.701s in that later interval. These are unmatched observation-time cohorts; overlapping stages are not additive causes of clientTTFT. Host/L3hits and additional uncached work remain recorded.

Next: one uniformopt-in earlier returned-bootstrap adoption trial, retaining9K/C05/output20 and the other ten candidates. The CPU screen advances eligibility one modelslot but cannot establish nativeprogress, KVcorrectness or performance. Freshall-rank activation, bounded correctness and full generator/load/window checks are required. The sharedbaseline localfailure timing limitation is preserved. After this bounded trial, allocate the planned1P4+D8 original-output/rejection-sampling slot. No6Mcapacityceiling or lowerloadfallback is established.
