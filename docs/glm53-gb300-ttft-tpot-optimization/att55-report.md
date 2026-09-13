# attempt55-two-prefill-utf8-frontend — strict TTFT trial not accepted

Alex measured run: [20260913_205103](http://43.156.43.133:31019/replay/runs/20260913_205103/report?view=overview&columns=overview). Full600s C05 traffic, output20, 9216token Prefill chunks. All **11,842 requests reached protocol success**, zero reported failures/empty/unadmitted. 17 responses lacked meaningful-generation timestamps; only 11825 contribute TTFT. Reported usage-token success does not prove useful output. Generator **invalid**. Outcome reasons: 17 protocol successes without meaningful generation; TTFT coverage incomplete, load generator invalid under original thresholds.

## Latency and generator

TTFT P50/P75/P90/P99 among requests with meaningful generation: **2.882916/3.477905/4.017349/4.978388s**. Original4/8/12/30s targets met: True; supplied1.2-timescontractlimits met: True. The every20sP50<4s researchtarget remainsstrict. All603Alex trailing20s completion-window points were independently reconstructed. **0/603windows reach or exceed4s**; worst **3.973114s at429.0s**, 379samples. Failingpointseconds and hashes are in`evidence/ANALYSIS-PROVENANCE.json`.

Generator lagp99 **50.113008ms**, admissionp99 **33.511500ms**, body-sendp99 **41.735471ms**, connectorwaits **0**. The original50/50/100ms limits are unchanged. No CPU stacks or locals probes were added.

## Load and cache

Input600,333,408, cached539,393,984, uncached60,939,424tokens. Hit89.849070%; net finite-plan uncached excess935,040tokens. Full600s input/uncached TPM: 60.033341M/6.093942M. All42,621exactfull60sadmission-windowstates checked; engineering-band acceptance **True**. Bands59.4–60.6M input/5.7–6.3Muncached are recorded engineering checks, not contract tolerances or physical GPU throughput. Storeevictions47, cumulativechurn2,957,291,272,704bytes; unchanged1300GiBrawcapacity. No6Mcapacityceiling follows from an unsuccessful trial.

## Recipe, validation and limits

For ATT55, the only serving delta is the frontend native-wheel repair/rebuild; `preparation/NATIVE-ARTIFACT-VERIFIED.json` and `parser-REPORT.md` preserve the exact patch, build and lock-reconciliation limits. Worker startup facts are inherited only from byte-for-byte identical pod/container bindings; fresh correctness requests still run. The separately recorded eight-token model-metric initialization ended on reasoning and was not a canonical or performance pass.



Two4GPUPrefills132/151 and one distributed8GPUDecode130/192. The recipe contains 11 performance candidates, including the opt-in startup logits-budget hook. Recorded delta: Only frontend mounted native wheel path and its rollout annotation; GLM UTF8 boundary repair, retainedMiniJinja2.22 and reviewed bindings-lock reconciliation. Allworker/source/topology/sampling/routing/Store specs unchanged. Frontend incarnation and affinity state reset. Exact source and render checks are in`preparation/PREPARED.json`. Prefill replacement changes incarnations/routing assignments, so cross-run differences are observational. All eight startupbudgetlogs, actualgraphs/ranks/capacities and frozenDSAgetter/defaultfraction checks are retained under`evidence/`. Decode rejection sampling is enabled on both physical Decode nodes, as recorded in the runtime attestation. Changes to both sampling mode and Prefill code prevent attributing cross-run gains to either alone.

Canonical6andaffinity4validationreceipts are in`evidence/CORRECTNESS-DRAINED.json` and`AFFINITY-CORRECTNESS-DRAINED.json`; inspect any explicitly marked inheritance. Freshwarmup20260913_204641 completed400/400, generatorvalid, coldTTFTP50/P99 17.535467/23.105950s. Coldwarmup is separate frommeasuredperformance. KVcache resets do not themselves clearfrontendbindingmaps.

All115queuegauges wereidle twice, everycollectorjoined, allboundsource/containeridentitiesrechecked. The frontend native hash is checked again when recorded in this arm state. Persistentserving remainsretained. TPOTtailwork is deferred: 50requests>40ms/32>80ms; 117windowswithp99>40ms. No fullTPOTcontract certification or generalKVaccuracyguarantee is claimed.

## Reproduction

`chart/`, `preparation/values.json`, `preparation/runtime-render.yaml`, `rollout/INTENT.json` preserve the exactrecipe/delta/rollback. `candidate/`, any `lifetime-candidate/` and`preparation/complete-eleven-candidate-against-frozen.patch` preserve source and native qualification evidence; reconstruction receipt sitsbesidethepatch. `runtime-bound.json`, `gate-execution/` and`evidence/` preserveactualstartupandchecks. `replay/` containsgeneratorconfig,cache-reset,allmetrics,accountingandloadvalidation. Rawtimingexport: `../evidence/20260913_205103/`; latencyreconstruction:`../evidence/latency-comparison-20260913_205103.json`. The immutablemilestonearchive is created onlyafter thisrecordcloses; its verifiedmanifest/hash live under`../milestones/attempt55-two-prefill-utf8-frontend/`. Rawrequests/credentialsareexcludedfrompublicreports.
