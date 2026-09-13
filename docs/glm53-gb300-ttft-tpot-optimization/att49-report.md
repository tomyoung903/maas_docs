# attempt49-two-prefill-8k-compressed-logits — strict TTFT trial not accepted

Alex measured run: [20260913_172724](http://43.156.43.133:31019/replay/runs/20260913_172724/report?view=overview&columns=overview). Full600s C05 traffic, output20, 8192token Prefill chunks. All **11,842 requests succeeded**, zero failures/empty/unadmitted. Generator **invalid**. Outcome reasons: load generator invalid under original thresholds, 19/603TTFTwindows>=4s, one or more recorded load/cache engineering bands missed.

## Latency and generator

Whole-run TTFT P50/P75/P90/P99: **2.855329/3.510149/4.106145/5.207214s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All603Alex trailing20s completion-window points were independently reconstructed. **19/603windows reach or exceed4s**; worst **4.345156s at508.0s**, 377samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **51.597988ms**, admissionp99 **32.934501ms**, body-sendp99 **40.094612ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,413,184, uncached60,920,224tokens. Hit89.852268%; net finite-plan uncached excess915,840tokens. Full600s input/uncached TPM: 60.033341M/6.092022M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **False**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,956,931,965,440bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits



Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The recipe contains 10 performance candidates, including the opt-in startup logits-budget hook. Recorded delta: Only Prefill chunk10240to8192,max-prefill-tokens10240to8192,andremove10240graphshape. TwoPrefillpodsroll; sixotherpod/containeridentitiesfixed. Allsources/images/resources/traffic unchanged. Exact source and render checks are in`preparation/PREPARED.json`. Prefill replacement changes incarnations/routing assignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Rejection sampling remains prepared for the later12GPU1P1D task; it is not enabled here.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_172444 completed400/400, generatorvalid, coldTTFTP50/P99 18.407657/23.963992s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. Persistentserving remainsretained. TPOTtailwork is deferred: 18requests>40ms/18>80ms; 0windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/`, any `lifetime-candidate/` and`preparation/complete-ten-candidate-against-frozen.patch` preserve source and native qualification evidence; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_172724/`; latencyreconstruction:`../evidence/latency-comparison-20260913_172724.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt49-two-prefill-8k-compressed-logits/`. Rawrequests/credentialsareexcludedfrompublicreports.

## Interpretation at closure

ATT49 does not replace ATT47. Its generator lag p99 was51.598ms against the unchanged50ms maximum. Six of42,621 load-window states exceeded6.3M uncached TPM, peaking6.319282M; every input-load state passed. Nineteen chart points reach4s:132,136–137,436–438,502–514. The worst is4.345156s at508s. Global P50/P99 are diagnostic observations, not accepted performance.

For nominal480–510s, the two Prefill PP0 queue counter means were1.896/1.445s, versus forward0.817/0.800s, bootstrap0.599/0.576s, final handoff0.633/0.600s. These observation-time counter populations are not matched requests and must not be added into a TTFT decomposition. Storage-hit increments were43,200/10,688tokens; this does not establish a shared-Store read burst as the cause. Extra finite-plan uncached demand was915,840tokens overall, larger than ATT47/48.

The next selected investigation is a9K intermediate Prefill quantum, keeping all ten sources and traffic settings. Invalid ATT49 is usable as the exact current runtime recipe and closed operational baseline; it is not a valid performance control. The next replay must independently pass the original generator/load/correctness/latency gates. ATT47 remains the best valid reference. No6M capacity ceiling or fallback is established.
