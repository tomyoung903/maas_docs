# Code and configuration ledger

These are experiment changes. No claim is made that they were merged into the main SGLang branch or deployed to production. The shared SGLang working tree has unrelated user edits; they are not part of the experiment snapshots.

## Retained serving code

Frozen SGLang: `/mnt/HPC/tom/experiments/glm53-optim-exp-1p1d/sources/sglang-6d08e28b0c0691899973e3f11bf01fdbdf192a63`.

The six original optimizations modify `scheduler_pp_mixin.py` and `prefill.py`: earlier control-bundle publication; forward launch before prior-output handling; earlier prior-output publication; early transfer of already cached prefix KV; final page-map reuse; same-iteration nonfinal page-map copy overlap. Their cumulative patch is preserved at `/mnt/HPC/tom/pd-queue-overnight-20260912.twotxxas/candidates/same-iteration-map-copy/cumulative-against-frozen.patch`, with reconstruction and lifetime/ordering checks next to it.

The later producer CUDA-event fix waits for KV-producing GPU work before transfer. It is retained in `candidates/optimized-async-kv-event/event-on-six-patches.patch`. That patch is incremental on the six optimizations, not a complete patch against frozen source. The complete files actually mounted into the workers are in each arm's `chart/files/`; corresponding `chart/templates/` and the rendered DGD specify mounting and startup order.

Current Prefill hashes through ATT35:

| File | SHA256 |
|---|---|
| `srt/managers/scheduler_pp_mixin.py` | `b3b95b176a6185a34b75664cda8aecc921989b9e50fa5efea268d3e207c07d41` |
| `srt/disaggregation/prefill.py` | `03a7e10add300de5bb51cefe767e49dd84187b375c998c7a16341230ea603ac3` |
| `srt/disaggregation/mooncake/conn.py` | `f34c28b27d812835d7b36d8074c12853aeb169a7c3261046c773262d304581ff` |

Actual per-role source verification and image/container IDs are recorded in `evidence/runtime-attestation.json`, `runtime-bound.json`, and final `replay/evidence/DRAINED.json`. A filename or image tag alone is not source verification.

## Combined reproducible source patch

`candidates/optimized-async-kv-event/complete-against-frozen.patch` combines the six optimizations and producer-event wait against frozen SGLang commit `6d08e28b0c0691899973e3f11bf01fdbdf192a63`. It applied cleanly to fresh copies of the three original files, and all reconstructed SHA256 hashes exactly match the runtime verified in ATT33. Patch SHA256: `44a9e0aa6f2e9d897c1aad7e2310d057c5cddcf5ad9a89278903343589713c9c`. Verification: `complete-patch-verification.json` beside the patch. Other pre-existing runtime overlays remain dependencies.

This combined export was finalized after the ATT33 milestone archive; that archive already includes the complete mounted chart files. It is preserved as an additional source artifact, not a retrospective runtime change.

## Recent configuration changes, with no new serving-code patch

| Arm | Change | Exact recipe |
|---|---|---|
| ATT31 | Candidate05 workload and 8K Prefill graphs | `attempt31-two-prefill-matched-rate/preparation/` |
| ATT32 | Frontend session-affinity TTL 1800s | `attempt32-two-prefill-session-affinity/preparation/` |
| ATT33 | Frontend projected-load escape threshold 8000ms → 0; affinity retained | `attempt33-two-prefill-strict-affinity/preparation/` |
| ATT34 | Both Prefill chunk/max-prefill limits 8192 → 12288 and matching graph size; all frontend/Decode/Store settings retained | `attempt34-two-prefill-12k-strict-affinity/preparation/` |

ATT35 is an unchanged repeat of ATT34 after its generator failed the existing50ms event-loop-lag gate. No runtime/source/image/resource/validation changes are made; it retains all eight pod/container incarnations and uses a fresh cache reset. Its copied recipe, fresh attestations and reused bounded-check provenance are explicit in `attempt35-two-prefill-12k-repeat/preparation/PREPARED.json`. It is a new experiment record, not a new serving-code change.

Each rollout directory contains before/trial values, complete before/after renders, a machine-checked scope diff, command, rollback command and SHA256 hashes. ATT34 changes only two Prefill pods; six other pod/container incarnations must remain unchanged. This control asks whether Prefill throughput headroom reduces TTFT queues with locality already improved.

## Native frontend provenance

Active native extension SHA256: `940d698e115b88236ed1266f3f8b78daf0471c1159a26ccf0fe83a4264f87d3f`. Installed wheel SHA256: `6b6bd53e3ce2fe0d7b67dca4e4f02690a3d5439bb6d4886bc20b23355a006a6b`. Retained wheel and launcher: `/mnt/HPC/tom/experiments/glm53-optim-exp-1p1d/native-patches/minijinja222-dc392/`.

The wheel's referenced Dynamo commit is `dc39202c7d67a76f40efab53d1cfc3485489d838`, parent `ff778ed59d00979737e278d228ddbfe32b82c296`. Read-only GitLab metadata shows this change affects dependency locks and a GLM reasoning test, not the affinity selector/coordinator. A complete build receipt excluding uncommitted source changes is still unavailable. Keep that limitation; the exact installed binary and wheel are preserved.

## Reproduction discipline

Use the arm's complete chart and values, not only the incremental patch. Recheck live ownership, exact namespace/release, no active replay, idle queues and resource scope before applying. Verify source/image identities and all intended ranks after rollout. Run bounded retrieval/L3/routing checks, then the recorded fresh-cache warmup and exact measured schedule. Preserve every outcome, including failed setup checks, unknown counters and interrupted replays. Do not replay stale pod IDs blindly.

Historical preparation state, superseded by the amendment below: ATT36 was prepared only: Prefill chunk/max-prefill12288→10240 and graph-size12288→10240. All serving source/images remain unchanged. The rendered scope check found only these three Prefill arguments changed. Apply is gated on completed valid ATT35, full accounting, collector closure, idle queues and fresh ownership/identity checks. Initial Prefill bindings will change with worker IDs; frontend/Decode session retention is recorded separately. Recipe: `attempt36-two-prefill-10k-strict-affinity/preparation/`.

## Generator investigation after ATT35

ATT35 closed with all requests successful but a second invalid generator result (event-loop lag p99 51.507188ms >50ms). At that checkpoint ATT36 was prepared and held; the later amendment/apply below supersedes that state. No serving or generator application source, resource, image or validation limit has changed. `worker/cpu_generator_callbacks.py` replays saved callbacks in a separate CPU-only process; `worker/run_cpu_generator_callbacks.py` records its exact source hash, bound container, stdout and exit status in `generator-cpu-audit/`. Hypotheses and controls are separate from proven findings.

ATT35 retained all session-to-worker placements from ATT34 despite fresh KV reset. This state factor and inherited bounded-check provenance are part of its reproduction record.

ATT36 decision amendment: the original valid-ATT35 prerequisite is preserved in `preparation/PREPARED.json` and `apply-original-valid-baseline-gate.py`. `preparation/DECISION-AMENDMENT.json` allows the next investigation after both CPU controls close, using valid ATT33 as a reference and ATT34/35 only as diagnostics. Every original acceptance threshold remains. The prepared observer reduces our active status query from three snapshots to one every15s; it does not modify the generator application. No isolated chunk-size causal estimate is claimed. `worker/alex_status_single.py` recovered ATT35’s entire final summary exactly; its live path will be checked at warmup.

At 2026-09-13T17:45:58.184127+08:00 ATT36 applied only the three prepared Prefill arguments for10K chunk/max-prefill/graph size. Watcher session34037 is checking both Prefill replacements while preserving the other six incarnations. No benchmark has started. Prior held/prepared states above remain historical.

ATT36 also records OS scheduling/cgroup counters for the exact measured Alex child with `worker/sample_generator_process.py` (10Hz process counters,1Hz CPU cgroup counters). This is an external read-only observer, not a Python hook. Kernel schedstats availability is recorded, so unavailable zero counters cannot be presented as absence of contention. The sampler must finish and be joined before the milestone closes.

ATT36 finalized 2026-09-13T18:18:24.558013+08:00: serving remains10K andidle afternegativeguardstop. No additional serving-source patch; the combined seven-change patch is unchanged. `REPORT.md`, exactrenders/bindings, rawtimings, stopreceipt, partialload/storeaudits, placementcounts andOSsamplingclosure are preserved. New analysis/recordkeeping utilities: `worker/audit_partial_load_cache.py`, `compare_10k_stages.py`, `record_tool_session.py`; expandedmilestonesnapshot includes observer/guard receipts. These utilities do not mutate serving code.

ATT37 preparation: unchanged10K runtime andall8pod/containeridentities. `worker/prepare_unchanged_10k_diagnostic.py` preserves recipe and inheritedboundedcheckprovenance; freshcache reset/allrankflush andgeneratorattestation passed. New `worker/capture_prefill_cpu.py` and `analyze_prefill_cpu.py` bindexacteightPIDs/birthtimes anduse2Hz/120s nonblockingCPUstacks. They arediagnostic observers, notservingsourcechanges.

ATT38 diagnostic closure: seven retained serving changes unchanged. `attempt38-two-prefill-logits-budget-probe/probe_logits_budget.py` preserves the actual bounded numeric probe. 88MB/252split finding is evidence, not a fix. Startup-budget candidate will be tracked separately with its complete source diff, tests, rollout and rollback receipts.

Candidate8 (not retained/qualified yet): `candidates/startup-logits-budget/startup-budget.patch`, SHA256`ea6cc26332dd13f58caf2275aabd7a10382d1e123f60a35bd83be2581754c67f`. One startup hook aftercapture/resize/weightfinalization, PrefillCUDAoptin, unchangedgetterfreefraction/staticguard.11CPUfixtures passed. Source/base/rollback are preserved in ATT39; no production merge.

ATT39 applied 2026-09-13T18:58:31.575630+08:00 through the existing owned Helm release. Only Prefill environment and the scheduler source mount changed; readiness and live tests remain pending. Complete seven retained changes plus candidate8: `attempt39-two-prefill-startup-logits-budget/preparation/complete-eight-candidate-against-frozen.patch`, SHA256 `48a16944ecb09fea4b2dca5d7e8520ca8c5821ad7f54a51981c2d1f8ef0e884c`; all four files reconstructed exactly (`COMPLETE-PATCH-VERIFIED.json`). The candidate/base/diff and CPU checks are read-only local files. `rollout/INTENT.json` preserves the precise ATT38 rollback command; `APPLIED.json` is apply evidence, not readiness evidence.

ATT40: first full valid test of candidate8 on unchangedATT39runtime. Observedp50/p992.967/5.334s,20failingTTFTwindows;notstrictpassorisolatedcausalestimate. Fullsourcepatchandruntimehashes retained. Tomaddedrejection-samplingflagforsecondary12GPU1P1D;preparedonlyundersecondary-1p1d-12gpu/rejection-sampling,notenabledin2P1D. DraftPRs/devandflags-onlyissuedeferreduntil2P1Dsorted.

ATT41: configuration-only12Kchunk/max-prefill/matchinggraph trial oncandidate8. No newservingcode; sourcepatchremains48a16944ecb09fea4b2dca5d7e8520ca8c5821ad7f54a51981c2d1f8ef0e884c. TwoPrefillincarnationsandroutingassignmentschange; recordascomparabilityfactor. Prior10K ATT40recipeisrollback. Candidate9notclaimed.

attempt41-two-prefill-12k-startup-budget: config-onlychunk12288onstartupbudgetcandidate8. Run20260913_125341;observedTTFTP50/P993.198/5.595s,19failingwindows;generatorvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. No additionalservingcodeorPRcreated.

attempt42-two-prefill-8k-startup-budget: config-onlychunk8192onstartupbudgetcandidate8. Run20260913_132716;observedTTFTP50/P992.934/5.659s,32failingwindows;generatorinvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. No additionalservingcodeorPRcreated.

2026-09-13T22:05:12.142587+08:00 — Optional diagnostics prepared only: existing Prefill device-timer flag/render in`candidates/prefill-device-timer-from-att43/`; allocator-counter observer source/patch and11actual-method CPUguard checks in`candidates/prefill-allocator-counters/`. Neither is selected/applied; neither joins the retained eight performance candidates. No allocator tuning or PP layer repartition performed.

ATT43:config-only6K trial on retained eight-candidate source; severe queue regression, no new serving source. Startupfailure retained separately. Return10K with prepared diagnostics next; noPRyet. `attempt43-two-prefill-6k-startup-budget/REPORT.md`.

ATT44 prepared:retained eightperformancecandidates plus separate opt-in Prefill allocator diagnostic, sourceb4ff6631eacd6d7cbe68f44c03b45d0af254b9ca70300abba23d59e40b3e7ffa.11CPUchecks; nativeunvalidated. Built-in device timer alsoenabled. `attempt44-two-prefill-10k-timing-allocator/diagnostic-candidate/`; noadditionalperformanceclaim/PR.

2026-09-13T22:36:29.127172+08:00:offline MQA logits-lifetime candidate only, NOTselected/applied. Release consumed score reference before next chunk allocation; unchanged budgets/math/mapping.44 actual-loop CPU cases with baseline negative controls reduce simultaneous fake score references2→1 across multi-chunk cases. Source32cd585d0307c0704db8d2810375b9789f7dbe49dbda74751fe467b23a0d9c2b; patch9f7f56dfd597da9dca8c0649832c4dc4c8e3ab7fc06d5e8132f3a20354fac0e1. Native stream/capture/allocator/numerical/performance validation pending; ATT44 still runs unchangeddiagnostics. `candidates/mqa-logits-lifetime/`.

attempt44-two-prefill-10k-timing-allocator: chunk10240onstartupbudgetcandidate8;instrumented=True. Run20260913_143815;observedTTFTP50/P993.032/7.101s,79failingwindows;generatorvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. Separate allocator diagnostic source and native timer; no additional performance candidate or PR.

2026-09-13T23:08:48.436445+08:00—Candidate9selectedforATT45pendingrollout: `candidates/mqa-logits-lifetime/release-logits-chunk.patch`; source32cd585d0307c0704db8d2810375b9789f7dbe49dbda74751fe467b23a0d9c2b. Native05has24cases andsame-stream/CUDAgraph checks; exactselectedmultisets,notorder. Native01UUIDformatstop/02unordered-outputoraclefailure/03FP32referencechecksretained. Nativequalifiedforboundedservingtrial,notmodelaccuracyorspeedupproof. Complete9patch inATT45/preparation,5sourcefilesverified.

2026-09-13T23:19:22.503566+08:00—Candidate9selectedforATT46pendingrollout: `candidates/mqa-logits-lifetime-ragged/release-logits-chunk.patch`; source182f5b863e82b3075f7ecf3dadf15047f283a967874b80be905f46a8822ce841. RAGGEDrevision native01has24cases; native02has6longKcases/1graphcheck. Originalunconditionalnative06failedPAGED; baseline07reproducedvariation. PAGEDbranchASTunchanged. Native01has24cases andsame-stream/CUDAgraph checks; exactselectedmultisets,notorder. Originalunconditionalcandidate native01-07evidence retained under its own path. Nativequalifiedforboundedservingtrial,notmodelaccuracyorspeedupproof. Complete9patch inATT46/preparation,5sourcefilesverified.

attempt46-two-prefill-ragged-logits-lifetime: chunk10240with9performancecandidates;instrumented=True. Run20260913_153855;observedTTFTP50/P992.980/5.203s,31failingwindows;generatorinvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. 9 recorded performance candidates; delta: Two Prefills only: one read-only DSA indexer source mount/volume plus immutable ConfigMap. Release consumed score reference only for RAGGED before next subchunk allocation; retain PAGED lifetime/operations unchanged. Keep ATT44 diagnostics, startup budgets/getter/defaultfraction,10K,all other sources/args/env/resources/cache/C05/output20 unchanged. No PR created. Allocator diagnostics and timer are separately recorded.

ATT47: no new performance source candidate. Remove only native device-timer flag and opt-in allocator reporter flag/mount/volume; restore source97010655. Retain nine performance changes, including RAGGED-only release. ATT46completepatch applies unchanged. FreshPidentities are a comparison factor; no isolated observer-overhead estimate. Preparation path mistake retained underpreparation-failures/att47-reporter-path-01.

2026-09-14T00:24:19.355403+08:00 — OFFLINE only: compact RAGGED MQA logits candidate `candidates/mqa-compressed-logits/`, source2ca8ca1e5616b140343c95126ad7dbb20d716974edfaad86c0c760795a0668a6. Exact five-file complete-ten recipe patch verified under `recipe-option/`; tenth candidate is not selected/applied/native-qualified. Flag TOM_DSA_COMPRESSED_MQA_LOGITS defaults off; proposed Prefill env1. Noncompact full-method AST projection reproduced with a wrong-row-start negative control. Native full-method/ABI/graph test and bounded idle launcher prepared, blocked until ATT47 terminal closure/archive. ATT47 currently uses9candidates, no additional diagnostics.

Secondary original-output guard: `secondary-1p1d-12gpu/control-template/GUARD-PREPARED.json` records14policy+8actual-drain-helper mock transport checks. Per-DP-stage88/96; low free+evictable KV with prealloc or PP0queue120 sustained15s; stale/missing/duplicate/invalid series stop own admissions. No totalactive-only350 limit. NOT activated: fresh7pod/rank/capacity and sampling/payload gates required. Rejection sampling remains prepared only.

attempt47-two-prefill-ragged-uninstrumented: chunk10240with9performancecandidates;instrumented=False. Run20260913_161656;observedTTFTP50/P992.885/5.202s,16failingwindows;generatorvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. 9 recorded performance candidates; delta: Two Prefills only: remove two diagnostic env flags and allocator reporter source volume/mount; restore frozen image reporter97010655. Retain all9performancecandidates,10K/C05/output20/Store/Decode/frontend/resources. Unused diagnostic ConfigMap retained. No PR created.

2026-09-14T00:36:02.328152+08:00 — Candidate10 selected for bounded ATT48 trial: `candidates/mqa-compressed-logits/compressed-mqa-on-ragged-lifetime.patch`; source2ca8ca1e5616b140343c95126ad7dbb20d716974edfaad86c0c760795a0668a6. Native qualification saved and processjoined. `ATT48/preparation/complete-ten-candidate-against-frozen.patch` (actualdirectory `attempt48-two-prefill-compressed-logits`) reconstructs all5modules. One Prefill opt-in flag TOM_DSA_COMPRESSED_MQA_LOGITS=1 and indexer source selector; no Decode rejection-sampling change here. No measured benefit yet.

attempt48-two-prefill-compressed-logits: chunk10240with10performancecandidates;instrumented=False. Run20260913_165356;observedTTFTP50/P992.887/5.469s,23failingwindows;generatorvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. 10 recorded performance candidates; delta: Prefill indexer source mount selector and opt-in env only, plus new immutable ConfigMap. Existing ConfigMaps retained. Other six serving pods, diagnostics-off, C05/10K/output20,resources and all other source unchanged. No PR created.

2026-09-14T01:25:58.925556+08:00 — Secondary controls/analysis only: baseline-derived Prefill chunk/graph checks,sevenpodDGD binding,5921terminal/load/cache/output analysis templates. HistoricalATT28 analyzer regressionpassed; no secondaryserving/RSactivation/PR. `secondary-1p1d-12gpu/TERMINAL-CONTROLS-PREPARED.json`. ATT49 changesonly3Prefillargs to8K,10performancecandidatesunchanged. 9Koptionnotselected.

attempt49-two-prefill-8k-compressed-logits: chunk8192with10performancecandidates;instrumented=False. Run20260913_172724;observedTTFTP50/P992.855/5.207s,19failingwindows;generatorinvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. 10 recorded performance candidates; delta: Only Prefill chunk10240to8192,max-prefill-tokens10240to8192,andremove10240graphshape. TwoPrefillpodsroll; sixotherpod/containeridentitiesfixed. Allsources/images/resources/traffic unchanged. No PR created.

2026-09-14T02:05:38.034649+08:00 — Candidate11 preparedonly: earlierreturnedbootstrapadoption, `candidates/early-returned-bootstrap/early-bootstrap-on-ten.patch`, sourced72dff03f17bc44e856d40e9ec6d05b707cc4895455c8642c2abb534f2f9b216. NewuniformdefaultoffTOM_PP_EARLY_BOOTSTRAP_ADOPT andoneperrankstartuplog. Existingreceive/adopt blockmovesbeforeselection; no ticket/fanout/newchannel. CPU5pairedcommcases,8healthyactualmetadata cases and11guardcasespass; mixedranknegativecaught;4actualmetadatafailurecasesretainbaseline-candidateequaldifferences, notoverallpass. Exactfive-file11candidatepatch7f29b09aff9b565c6cc98d667b5f2e29cc5a03f44540fce7776dfd4487b8d374. ProposedATT51materializerpreparednotexecuted. No serving/native/modelperformanceclaim.

attempt50-two-prefill-9k-compressed-logits: chunk9216with10performancecandidates;instrumented=False. Run20260913_180611;observedTTFTP50/P992.838/5.518s,2failingwindows;generatorvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. 10 recorded performance candidates; delta: Only Prefill chunk8192to9216,max-prefill-tokens8192to9216,andadd9216graphshape. TwoPrefillpodsroll; sixotherpod/containeridentitiesfixed. Allsources/images/resources/traffic unchanged. No PR created.

2026-09-14T02:57:35.282323+08:00 — ATT51candidate11REJECTEDatnative startup; noAlexreplay/noTTFTgain. Earlybootstrapadoption pluscoldfirstNCCLsend createdobservedprogresswaitconsistentwithrevisedCPUmodel. Source d72dff03 retainedforresearchonly; ATT52restores10-candidates9K. Controllerstalepod/RBACdenial/annotationrecovery preserved separately.

2026-09-14T03:15:47.204395+08:00 — Prepared primed early-bootstrap revision73aaee27, not deployed. One startup helper/call on rejected source, unchanged loop+guard AST. Exacthelper3cases and guard11cases pass; native tiny peer fixture supports mechanism only. primary-return-option includes verified complete11candidatepatch and315895BHelmpackage, based on ATT53 RS+9K withP1to2. Fullmodel/performance qualification pending. Retained successful source count remains10.

2026-09-14T03:49:44.962491+08:00 — attempt53-one-prefill-real-output-rejection:12GPU/originaloutputs/DecodeRSenabled; selectedprimarysource `/mnt/HPC/tom/pd-latency-followup-20260913/attempt52-two-prefill-9k-recovery`. Existingflag andfreshcompilegeneration, noflag-specificspeedupclaim. Recipe/reportretained; draftPRsremainafterprimaryresolution.

ATT54:11 performance candidates,9K chunks,primed earlier bootstrap73aaee27 on both Prefills; Decode rejection sampling retained. Partialrun20260913_200602failedinexistingfrontendUTF8slice atff778ed. Parserrepairisbeingpreparedseparately,notappliedinATT54. No6Mceilingclaim;noPRcreated.

ATT55 frontend repair: standalone GLM UTF8 boundary change plus2regressiontests, retaineddc392MiniJinja2.22;914CPUtests passed,84API names unchanged. Source/build/lock/artifact undercandidates/frontend-parser-utf8. Wheel7616ba116a7c,native462cdc2acf;mountedwheelhostPath+annotationonly,noGPUworkerrollout. All7otherincarnations retained. Livecorrectnesspending;notaperformancegainclaim. Stalebindinglockreconciliationandextratinymetricinitnegativeanswerpreserved.

attempt55-two-prefill-utf8-frontend: chunk9216with11performancecandidates;instrumented=False. Run20260913_205103;observedTTFTP50/P992.883/4.978s,0failingwindows;generatorinvalid;primarytrialaccepted=False. Incarnation/routingchanges preventisolatedcausalattribution. 11 recorded performance candidates; delta: Only frontend mounted native wheel path and its rollout annotation; GLM UTF8 boundary repair, retainedMiniJinja2.22 and reviewed bindings-lock reconciliation. Allworker/source/topology/sampling/routing/Store specs unchanged. Frontend incarnation and affinity state reset. No PR created.

attempt56-two-prefill-utf8-repeat: chunk9216with11performancecandidates;instrumented=False. Run20260913_211342;observedTTFTP50/P992.839/4.949s,0failingwindows;generatorvalid;primarytrialaccepted=False. Sameincarnations/settings retained; dynamicrouting/cachevariance andcombinedearlierchanges preventisolatedcausalattribution. 11 recorded performance candidates; delta: No source, image, native wheel, flag, topology, resource, Store or worker incarnation change. Fresh scoped cache reset/warmup; frontend routing state is retained. No PR created.
