# attempt48-two-prefill-compressed-logits — strict TTFT trial not accepted

Alex measured run: [20260913_165356](http://43.156.43.133:31019/replay/runs/20260913_165356/report?view=overview&columns=overview). Full600s C05 traffic, output20, 10240token Prefill chunks. All **11,842 requests succeeded**, zero failures/empty/unadmitted. Generator **valid**. Outcome reasons: 23/602TTFTwindows>=4s.

## Latency and generator

Whole-run TTFT P50/P75/P90/P99: **2.886835/3.383482/3.909061/5.468581s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All602Alex trailing20s completion-window points were independently reconstructed. **23/602windows reach or exceed4s**; worst **4.531822s at307.0s**, 385samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **35.970072ms**, admissionp99 **34.798356ms**, body-sendp99 **44.372531ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,619,456, uncached60,713,952tokens. Hit89.886628%; net finite-plan uncached excess709,568tokens. Full600s input/uncached TPM: 60.033341M/6.071395M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **True**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,958,155,458,560bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits



Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The recipe contains 10 performance candidates, including the opt-in startup logits-budget hook. Recorded delta: Prefill indexer source mount selector and opt-in env only, plus new immutable ConfigMap. Existing ConfigMaps retained. Other six serving pods, diagnostics-off, C05/10K/output20,resources and all other source unchanged. Exact source and render checks are in`preparation/PREPARED.json`. Prefill replacement changes incarnations/routing assignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Rejection sampling remains prepared for the later12GPU1P1D task; it is not enabled here.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_165037 completed400/400, generatorvalid, coldTTFTP50/P99 17.171479/22.933184s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. Persistentserving remainsretained. TPOTtailwork is deferred: 40requests>40ms/36>80ms; 87windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/`, any `lifetime-candidate/` and`preparation/complete-ten-candidate-against-frozen.patch` preserve source and native qualification evidence; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_165356/`; latencyreconstruction:`../evidence/latency-comparison-20260913_165356.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt48-two-prefill-compressed-logits/`. Rawrequests/credentialsareexcludedfrompublicreports.


## Follow-up decision

ATT47 remains the best valid2P1D reference. ATT48's full-run p50 is essentially unchanged (2.886835versus2.885089s); p99 is higher (5.468581versus5.202355s), and23windowsfail comparedwith16. The worst20smedian is4.531822s at307s; allfailingpointsformoneinterval299–321s. Native scratch-layout savings did not establish a latency improvement in this serving run. ChangedPrefillincarnations/routing and cache variation prevent isolated attribution to the compact-logits candidate.

All42,621admission-windowloadstatespass the retained engineering bands. Measureduncachedtokens60,713,952, hit89.886628%, finite-plan excess709,568. Storeevictions47, churn2,958,155,458,560bytes. No6Mcapacityceiling is established and no5.6Mfallbackisjustified.

The270–300sobservation interval hasP132meanqueue1.594422s versus0.679502sat60–90s; P151meanqueue0.861858s versus0.324652s. In300–330s the queue means are0.993594s and1.109641s. Forward means remainaround0.90–0.97s inthesehotintervals. These are unmatchedPP0countercohorts, not additive TTFT stages or a matched causal breakdown. Shared-storehitcounterincrementsarelowduring270–330s, so a largeL3readburstisnotdemonstratedforthisspike. Noallocatorretrycountwascollectedinthisdiagnostics-offtrial.

A smaller8Kchunk is the next candidate for review onthecurrentcompactrecipe: reduce scheduling/forward quantum while preserving allother source/traffic settings. The older8KATT42 hadinvalidgenerator and lackedthetwo laterRAGGEDcandidates, so it doesnotsettlethecurrentconfiguration. A newtrialneedsfreshsource/topology/graph/cache/correctness/warmup/loadgates. The secondary12GPUrejection-sampling recipe and controls areprepared separately; no12GPUactivationorPRworkhasbegun. The02:00resourceallocationcheckpointremainsinforce.

The workload analyzer's inheritedreasontext incorrectlysaid10Kdiagnostic/startupbudgetonly. `evidence/ANALYSIS-METADATA-CORRECTION.json` records the correction toATT48compact/diagnostics-off; every numeric and otheranalysisfield is unchanged.
