# attempt47-two-prefill-ragged-uninstrumented — strict TTFT trial not accepted

Alex measured run: [20260913_161656](http://43.156.43.133:31019/replay/runs/20260913_161656/report?view=overview&columns=overview). Full600s C05 traffic, output20, 10240token Prefill chunks. All **11,842 requests succeeded**, zero failures/empty/unadmitted. Generator **valid**. Outcome reasons: 16/603TTFTwindows>=4s.

## Latency and generator

Whole-run TTFT P50/P75/P90/P99: **2.885089/3.439879/4.060896/5.202355s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All603Alex trailing20s completion-window points were independently reconstructed. **16/603windows reach or exceed4s**; worst **4.135897s at295.0s**, 363samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **43.443828ms**, admissionp99 **34.146460ms**, body-sendp99 **42.033429ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,669,248, uncached60,664,160tokens. Hit89.894922%; net finite-plan uncached excess659,776tokens. Full600s input/uncached TPM: 60.033341M/6.066416M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **True**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,958,988,561,152bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits



Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The recipe contains 9 performance candidates, including the opt-in startup logits-budget hook. Recorded delta: Two Prefills only: remove two diagnostic env flags and allocator reporter source volume/mount; restore frozen image reporter97010655. Retain all9performancecandidates,10K/C05/output20/Store/Decode/frontend/resources. Unused diagnostic ConfigMap retained. Exact source and render checks are in`preparation/PREPARED.json`. Prefill replacement changes incarnations/routing assignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Rejection sampling remains prepared for the later12GPU1P1D task; it is not enabled here.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_161102 completed400/400, generatorvalid, coldTTFTP50/P99 17.775604/23.403668s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. Persistentserving remainsretained. TPOTtailwork is deferred: 25requests>40ms/22>80ms; 55windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/`, any `lifetime-candidate/` and`preparation/complete-nine-candidate-against-frozen.patch` preserve source and native qualification evidence; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_161656/`; latencyreconstruction:`../evidence/latency-comparison-20260913_161656.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt47-two-prefill-ragged-uninstrumented/`. Rawrequests/credentialsareexcludedfrompublicreports.

## Follow-up decision

ATT47 is the new best valid 2P1D reference by full-run p50/p99, worst short-window median, and count of failing windows compared with ATT40. It still fails the strict target: nine consecutive points at139–147s and seven at294–300s reach4s. Both runs pass the recorded load/cache bands, but route assignments, Prefill incarnations and cache misses differ; this is observational improvement, not isolated attribution to the ninth patch or removed diagnostics.

During the120–150s observation interval, P151 PP0 mean queue time was1.418s versus0.568s at60–90s. During270–300s, P132 mean queue time was1.107s versus0.374s at60–90s. These unmatched counter cohorts support continued Prefill work; overlapping stages cannot be added as causal TTFT components. No additional allocator/device-timer instrumentation was active, so ATT47 does not establish an allocator-retry count.

The local initial preparation failure is retained at `../preparation-failures/att47-reporter-path-01/`: an incorrect reporter path failed before serving mutation. The corrected preparation resolved the frozen reporter path/hash and applied only the intended diagnostic removal.

The next prepared candidate is `../candidates/mqa-compressed-logits/`, not yet native-qualified, selected or applied. It proposes request-relative MQA score storage with the same KV output offsets. Native validation is permitted only after this run's closure/archive and fresh idle/headroom checks. The shared16GPU primary remains retained; the 12GPU real-output/rejection-sampling experiment is still prepared only. No5.6Mfallback or draft-PR work has begun.
