# attempt56-two-prefill-utf8-repeat — strict TTFT trial not accepted

Alex measured run: [20260913_211342](http://43.156.43.133:31019/replay/runs/20260913_211342/report?view=overview&columns=overview). Full600s C05 traffic, output20, 9216token Prefill chunks. All **11,842 requests reached protocol success**, zero reported failures/empty/unadmitted. 23 responses lacked meaningful-generation timestamps; only 11819 contribute TTFT. Reported usage-token success does not prove useful output. Generator **valid**. Outcome reasons: 23 protocol successes without meaningful generation; TTFT coverage incomplete.

## Latency and generator

TTFT P50/P75/P90/P99 among requests with meaningful generation: **2.839280/3.434900/3.978203/4.948596s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All603Alex trailing20s completion-window points were independently reconstructed. **0/603windows reach or exceed4s**; worst **3.897844s at507.0s**, 401samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **46.973485ms**, admissionp99 **34.135987ms**, body-sendp99 **40.692322ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,393,984, uncached60,939,424tokens. Hit89.849070%; net finite-plan uncached excess935,040tokens. Full600s input/uncached TPM: 60.033341M/6.093942M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **True**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,958,226,751,232bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits

ATT56 repeats ATT55 with all eight pod/container identities and all serving settings unchanged. No rollout or new source delta occurred. `rollout/UNCHANGED.json` and `evidence/REPEAT-PREFLIGHT-ATTESTATION.json` record the actual bindings. Canonical six-request and four affinity checks are explicitly inherited from ATT55; they were not rerun. Fresh generator attestation, scoped all-rank KV-cache reset and 400-request warmup preceded measurement. The repaired frontend native artifact remains qualified by ATT55; its full native build and both libraries are in the ATT55 milestone archive.



Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The recipe contains 11 performance candidates, including the opt-in startup logits-budget hook. Recorded delta: No source, image, native wheel, flag, topology, resource, Store or worker incarnation change. Fresh scoped cache reset/warmup; frontend routing state is retained. Exact source and render checks are in`preparation/PREPARED.json`. No Prefill or frontend replacement occurred in this repeat. Dynamic routing/cache state can still differ, so this repeat does not isolate effects of any individual earlier patch. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Decode rejection sampling is enabled on both physical Decode nodes, as recorded in the runtime attestation. Changes to both sampling mode and Prefill code prevent attributing cross-run gains to either alone.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_210758 completed400/400, generatorvalid, coldTTFTP50/P99 17.920165/24.144327s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. The frontend native hash is checked again when recorded in this arm state. Persistentserving remainsretained. TPOTtailwork is deferred: 38requests>40ms/19>80ms; 45windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/UNCHANGED.json` preserve the exact recipe and retained identities. The prior frontend rollout/rollback lives in the closed ATT55 archive. `candidate/`, any `lifetime-candidate/` and`preparation/complete-eleven-candidate-against-frozen.patch` preserve source and native qualification evidence; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_211342/`; latencyreconstruction:`../evidence/latency-comparison-20260913_211342.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt56-two-prefill-utf8-repeat/`. Rawrequests/credentialsareexcludedfrompublicreports.
