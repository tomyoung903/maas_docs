# attempt46-two-prefill-ragged-logits-lifetime — strict TTFT trial not accepted

Alex measured run: [20260913_153855](http://43.156.43.133:31019/replay/runs/20260913_153855/report?view=overview&columns=overview). Full600s C05 traffic, output20, 10240token Prefill chunks. All **11,842 requests succeeded**, zero failures/empty/unadmitted. Generator **invalid**. Outcome reasons: instrumented diagnostic; uninstrumented confirmation required, load generator invalid under original thresholds, 31/604TTFTwindows>=4s, one or more recorded load/cache engineering bands missed.

## Latency and generator

Whole-run TTFT P50/P75/P90/P99: **2.980194/3.533820/4.155456/5.203011s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All604Alex trailing20s completion-window points were independently reconstructed. **31/604windows reach or exceed4s**; worst **4.312874s at446.0s**, 381samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **56.411539ms**, admissionp99 **32.848648ms**, body-sendp99 **40.822039ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,481,728, uncached60,851,680tokens. Hit89.863686%; net finite-plan uncached excess847,296tokens. Full600s input/uncached TPM: 60.033341M/6.085168M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **False**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,957,744,512,512bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits

This arm uses the separately recorded opt-in allocator reporter and native device timer with 9 performance candidates. Native counter coverage and possible observation overhead are recorded under evidence/native-diagnostics-*. It is not an uninstrumented acceptance replay.

Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The recipe contains 9 performance candidates, including the opt-in startup logits-budget hook. Recorded delta: Two Prefills only: one read-only DSA indexer source mount/volume plus immutable ConfigMap. Release consumed score reference only for RAGGED before next subchunk allocation; retain PAGED lifetime/operations unchanged. Keep ATT44 diagnostics, startup budgets/getter/defaultfraction,10K,all other sources/args/env/resources/cache/C05/output20 unchanged. Exact source and render checks are in`preparation/PREPARED.json`. Prefill replacement changes incarnations/routing assignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Rejection sampling remains prepared for the later12GPU1P1D task; it is not enabled here.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_153543 completed400/400, generatorvalid, coldTTFTP50/P99 17.365802/22.377250s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. Persistentserving remainsretained. TPOTtailwork is deferred: 18requests>40ms/15>80ms; 20windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/`, any `lifetime-candidate/` and`preparation/complete-nine-candidate-against-frozen.patch` preserve source and native qualification evidence; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_153855/`; latencyreconstruction:`../evidence/latency-comparison-20260913_153855.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt46-two-prefill-ragged-logits-lifetime/`. Rawrequests/credentialsareexcludedfrompublicreports.

## Native findings and rejected preflight

Four measured allocator retries, zero allocator OOMs, and thirteen separate warmup retries were observed. Retry intervals were P132/PP1 at0.726–5.726,214.726–219.726,481.726–486.726s and P151/PP0 at441.726–446.726s. Failed20s-window ranges were440–456and500–513s. These are sampled counter observation intervals, not allocation durations or proof of causality. All8rank counters remained observable; complete watcher logs cover rotations in current pod logs. Detailed evidence:`evidence/native-diagnostics-findings.json` and`native-diagnostics-600s.json`.

The ninth candidate is RAGGED-only. Thirty native cases and three graph checks/fifty replays passed; the unchanged PAGED branch remains outside the new lifetime change. The earlier unconditional release failed a long-K PAGED test and was never deployed; repeated baseline PAGED checks also varied. Those negative results and the guarded revision are preserved under`lifetime-candidate/`, not treated as harmless variation or general correctness proof.

The first Helm apply failed at its release-secret size limit before any serving change. Packaging-only exclusions preserved the rendered manifest byte-for-byte; the retry passed. Both attempts and the no-serving-mutation audit are under`rollout/`. The next selected option removes only the two Prefill diagnostic env flags and reporter mount/volume, retaining all nine performance candidates and workload settings. No diagnostic-free performance claim has been made.
