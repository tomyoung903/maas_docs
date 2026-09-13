# Milestones — current 2P1D investigation

Primary goal, reaffirmed by Tom on 13 September: the same TTFT standard achieved in 1P1D, now with two Prefills and one eight-GPU Decode at approximately 60M input / 6M uncached TPM. Every Alex trailing 20-second completion-window TTFT p50 must stay below four seconds throughout the full 600-second test, with zero request failures. TPOT and extended correctness research are deferred unless they block this goal. Existing fixes and bounded regression checks remain.

| Milestone | Result | Durable record |
|---|---|---|
| Six scheduling/publication optimizations | Earlier control and output publication, forward launch, cached-prefix transfer and page-map overlap; experimental overlays, not merged production code | `CODE-CHANGE-LEDGER.md`; previous investigation archive |
| ATT25 → ATT27: KV producer ordering | Nonfinal-chunk KV mismatch localized; producer CUDA-event wait added; diagnostic tensors matched and bounded retrievals passed | `attempt25-pd-only-kv-fingerprint/`, `attempt27-async-kv-event/`, `candidates/pp-async-kv-event/` |
| ATT28: best complete 1P1D | 5,921 successes; zero failures; every 20s TTFT p50 below 4s, worst 3.064s; 30M/3M traffic. TPOT remains open | `attempt28-lane-b-optimized-event/REPORT.md`; Alex `20260913_050451` |
| Four-node deployment | Prefill132 + Prefill151; one distributed eight-GPU Decode130+192; private 1300GiB Store | `expanded-four-node/two-prefill-one-decode/` |
| ATT29: 8K 2P1D | Interrupted with Prefill backlog; 4,705 successes, zero failures; worst 20s TTFT p50 51.830s | Same directory, `REPORT.md`; Alex `20260913_055201` |
| ATT30: 12K control | Interrupted; 3,942 successes, 12 overload failures; worst 20s p50 22.219s. Older candidate04 and no session affinity | `attempt30-two-prefill-12k/REPORT.md`; Alex `20260913_063354` |
| Candidate05: matched request rate | Exact real-request identities, 11,842 measured requests, 400 warmup; approximately 60M/6M; source/token/payload checks preserved | `expanded-four-node/dataset/candidate05-matched-request-rate/` |
| ATT31: candidate05, 8K | Interrupted after backlog guard; 2,968 successes, zero failures; worst 20s p50 16.477s | `attempt31-two-prefill-matched-rate/REPORT.md`; Alex `20260913_070704` |
| ATT32: session affinity 1800s | Locality improved, but 14 HTTP400 binding conflicts; 956 successes; residual bootstraps cleared after 300s timeout | `attempt32-two-prefill-session-affinity/REPORT.md`; Alex `20260913_073337` |
| ATT33: strict affinity | Full 600s completed, 11,842 successes, zero failures/empty outputs. Worst 20s p50 6.116s; 213/603 windows above 4s. Hit 89.8904%; actual uncached approximately 6.069M TPM | `attempt33-two-prefill-strict-affinity/REPORT.md`; Alex `20260913_075613` |
| ATT34: 12K with strict affinity | 11,842 successes, zero failures; worst20s p50 4.571s,56/603 above4. Generator invalid: event-loop lag p99 50.390ms >50ms; diagnostic only | `attempt34-two-prefill-12k-strict-affinity/REPORT.md`; Alex `20260913_084212` |
| ATT35: unchanged12K repeat | 11,842 successes; worst20s p50 4.493s,60/602 above4. Generator invalid again:51.507ms>50; exact placement retained for all11,842 requests | `attempt35-two-prefill-12k-repeat/REPORT.md`; Alex `20260913_090354` |
| ATT36: 10K intermediate control | Interrupted by backlog guard:4,227 successes,0failures,7,615 never admitted. Valid generator31.889ms lag p99; worst20s TTFT p5012.322s,151/228 windows fail | `attempt36-two-prefill-10k-strict-affinity/REPORT.md`; Alex `20260913_100538` |

Latest phase and active process handles: root `STATUS.json` and the current arm's `STATUS.json` / `tool-sessions.json`. An applied configuration is not a completed experiment. Failed and partial arms remain in this table.

Published report: https://tomyoung903.github.io/maas_docs/glm53-gb300-ttft-tpot-optimization/

Closed milestones receive a private archive and verified file manifest under `milestones/`. The archive preserves code/configuration and evidence references; model data, images, credentials and external services remain reproduction dependencies.

ATT35 archive: `milestones/attempt35-two-prefill-12k-repeat/recipe-code-evidence.tar.gz`; 138 files verified, SHA256 `81ccff3efb2fbcd9c119ed336def4fb0be9f1e2a0b8d1254eced144157ceac9f`. Retained routing state is explicit: fresh KV reset did not clear frontend bindings; all 11,842 requests matched ATT34 worker placement.

CPU generator audit: `generator-cpu-audit/`; isolated saved-callback replay, no HTTP/model calls or serving changes. Each variant preserves its source hash, original stdout, exit status and result. This is a diagnostic, not an accepted serving test.

At 2026-09-13T17:45:58.184127+08:00 ATT36 applied only the three prepared Prefill arguments for10K chunk/max-prefill/graph size. Watcher session34037 is checking both Prefill replacements while preserving the other six incarnations. No benchmark has started. Prior held/prepared states above remain historical.

ATT36 before-load evidence: all sources/ranks/images verified, P KV9,252,096tokens/rank and D3,135,616tokens/rank unchanged; Store1300GiB unchanged. `attempt36-two-prefill-10k-strict-affinity/evidence/CORRECTNESS-DRAINED.json` reconstructs exact18,048-token L3reads on allfourPP ranks in both directions and actual10Kgraphs. Fouraffinityprobes passed. `INITIAL-ROUTING-STATE.json` records nofrontendcompletions forover33minafterATT35closure, exceeding1800sidleTTL.

ATT36 closed 2026-09-13T18:18:24.558013+08:00: every collector joined, all115queue gauges idle, exactsources/identities verified. Same retained seven source changes; onlythreePrefillarguments changed. Original gate amendment, lighterobserver, newplacements andOSsampler are recorded comparison factors. Bounded checks6+4 andwarmup400/400passed; primaryTTFT stillfails. Full60s windows withinpartialspan12155/12155 engineeringbandspass; Store13evictionpasses/818089450752byteschurn.

ATT36 immutablearchive finalized:184files/1245798bytes, allentryhashesverified, SHA256 `1e568706a1af2d373f1ef3b4ed26cde332e187b16340981a0ab0c338a33405cb`. ATT37 prepared as unchanged10KCPUdiagnosticrepeat: sameeightincarnations, inherited6+4boundedchecks, freshattestation/cache/warmuprequired. Bounded2Hz/120s CPUstacks planned for all8Prefillschedulers; diagnosticobserverfactor, noGPUtracing.

ATT37 closed:4,212 successes/0 failures,7,630 neveradmitted; worst20sTTFTp5014.229s,166/227windowsfail; generatorlag52.172ms>50ms. Unchanged10K diagnostic,7/8CPUprofiles recovered; exactownedP151PP0sampler requiredSIGKILLaftertimeout/SIGINTfailure. Allservingrequestsdrained,115gaugesidle. P151PP1 MQAlogits subchunkloop131/222samples vsP132PP1 2/213; actualbudgetvalues andcausalitynotyetobserved. `attempt37-two-prefill-10k-cpu-diagnostic/REPORT.md`.

ATT37 archive:196files/874278bytes,allentriesverified, SHA256 `e7ad31296caf8501fee2c04bac5765857a3cc3b8417b64f752ffd0960ed418de`. ATT38 numericbudgetprobe prepared withunchangedruntime; boundedtwoPP1readers only.

ATT38 closed 2026-09-13T18:50:48.801704+08:00:2,715success/0failure,manual diagnostic stop, all115gaugesidle/allcollectorsjoined. One coherent P151PP1 snapshot:88,067,276-byte MQA budget,10,077queries×538,333keys,40rows/split,252subchunks. P132 numeric budget unobserved; two inconsistent snapshots excluded. Valid generator;70/146TTFTwindows>4s. No serving patch applied; startup refresh through unchanged memory guards is next candidate. `attempt38-two-prefill-logits-budget-probe/REPORT.md`.

ATT38 archive finalized:217files/890350bytes, SHA256`d48412d5e7081b5e4fe4762d33e1c327db9bb77e2af10d7c89584b8f9142d3ef`. ATT39 prepared: one scheduler startup hook, source`85bbce778a5683b013c54824e29eef2119fcde27e50c8954183f7e9fe00bf63d`,11CPUcontracts passed; onlyPrefill env/mount rendered; notapplied yet.

Public ATT38 record verified 2026-09-13T18:58:31.575630+08:00: canonical and cache-busted GitHub Pages URLs returned200 and exact expected HTML SHA256 `f9bc554df635060ad1dbed3df70588e5e56cc7fdfaa1c77c6dce3c41c55c9126`; docs commit `2e34a149c29b39a8707439aa879f4d5578c3df39`. `docs/publication-att38.json` preserves the initial stale-cache check and successful verification.

ATT39 first-ready startup observation 2026-09-13T18:59:17.705425+08:00: new P151 had unset budgets on allfourPP ranks at the post-startup hook. PP1 initialized to8,910,624,522bytes under the original getter guards. This new run observes initialization before serving, not replacement of a warmup-cached value. Historical ATT38 first-use timing remains unobserved. Same-old-batch arithmetic would change252splits to3; this is not measured latency. Evidence: `attempt39-two-prefill-startup-logits-budget/evidence/INITIALIZATION-OBSERVATION.json`.

ATT39 resumed afterusage reset 2026-09-13T19:25:58.924494+08:00:sameeightboundincarnations reverified,115gaugesidle,noactiveAlex. Fresh6canonical+4affinitychecks passed, exact18048L3tokens/rank inbothdirections and10Kgraphuse, fullDecodeDP0–7flush. Freshgenerator/dataset/tokenhashes match. Warmup20260913_112533started; noCPU/localsprobes. Mainmeasuredresultnotyetavailable.

ATT39 userpaused 2026-09-13T19:28:41.918457+08:00:6canonical+4affinitypassed; warmup20260913_112533 completed400/400,0fail/empty,validgeneratorlagp995.866ms. ColdwarmupTTFTp50/p9917.184/22.488s. Full600smeasuredtest NOTstarted. NoactiveAlex;115gaugesidle twice; monitorstoprequested; servingresourcesremainallocated. `evidence/USER-PAUSED.json`.

ATT39 closed warmup-only: candidate8startup initialization applied;11CPU/6canonical/4affinity passed;400warmupsuccess,0fail,validgenerator; measurednotstarted. Pause/resume/source/idlechecks preserved. NewATT40willreuseexactruntimewithfreshcache/warmup. `attempt39-two-prefill-startup-logits-budget/REPORT.md`.

### 2026-09-13 20:15 Singapore — ATT40 full replay started

Unchanged candidate8 runtime from closed warmup-only ATT39, fresh complete generator/dataset attestation, full cache reset, and400/400successfulwarmup (121122;validgeneratorlagp992.341ms). Full600sC05/output20run121454 is active; no performance pass yet. Secondary12GPU topology is rendered offline with original3Mdataset/outputpolicy preserved. Deadline is14September10:00Singapore;2P1Dpriorityandconditionalfallback/deferreddraftPRs/flagsissue recorded inDEADLINE-GOALS-20260914.md.

### 2026-09-13T20:32:39.478043+08:00 — ATT40 best full valid2P1D result

11842success/0failure,validgenerator44.319547ms;TTFTp50/p992.966963/5.334008s.20/603windows>4s,worst4.531601s at573s.42,621rollingload/cache states pass;actual60.033M/6.080MTPM,89.871884%hit.24existingtracecohorts point towardPrefillqueueing. All115gaugesidle,collectorsjoined,source/identitiesverified. Samecandidate8runtimeasATT39. Next12Kchunk trial; goalnotyetpassed. `attempt40-two-prefill-startup-budget-replay/REPORT.md`.

### 2026-09-13T20:42:21.362700+08:00 — ATT41 scoped12K trial rollout

ATT40 archive verified before mutation. ATT41 changes exactly3Prefillarguments (chunk/max-prefill/graph10240→12288); samecandidate8source,C05/output20,strictaffinity,Store and sixnonPrefillincarnations. P151ready;P132starting. Fresh6canonical+4affinitychecks andcachewarmup required. `attempt41-two-prefill-12k-startup-budget/preparation/PREPARED.json`, `rollout/INTENT.json`. Secondaryoriginal-outputHTTPbodies compiled andall6021comparedwithoriginalpolicywhileprimaryidle,20.35s/noinference; `secondary-1p1d-12gpu/payload-preparation/VERIFIED.json`.

2026-09-13T20:50:29.800195+08:00: ATT41 bothPrefillsreadyafter507.331sreadinesswatch; actual12Kgraphs/frozencandidate8DSAsources,KV9252096tokens/PPrank,Decode3135616/DP,Store1300GiBverified. Eightstartupbudgetlogs:PP0/1=8910624522B,PP2=7401255731B,PP3=7020412928B,oldunset,bothPidentical. Fresh6retrieval+4affinitychecks allpass;L3cross-P18048tokensonall4ranksbothdirections. FourDSAsourcehashes/defaultfractionunchanged. FreshcompleteC05/generator/tokenmanifestattestationmatches. Scopedcache-resetbeforewarmupnowrunning.

### 2026-09-13T21:10:14.667886+08:00 — attempt41-two-prefill-12k-startup-budget fulltrialclosed

20260913_125341:11842success/0failure;generatorvalid;TTFTP50/P993.198143/5.594766s,worst20sP504.495855s,19/603windows>=4s. Load/cachebandsFalse;primarytrialacceptanceFalse. Samecandidate8source,12288chunks. All115gaugesidle,collectorsjoined,source/incarnationschecked. Exactrecipeandrollbackin`attempt41-two-prefill-12k-startup-budget/REPORT.md`.

### 2026-09-13T21:11:10.136766+08:00 — ATT42 8K startup-budget test selected

ATT41 valid full run:19/603 windows>=4s,worst4.496s,globalP50/P99=3.198/5.595s;28 exact60sloadstates exceeded6.3Muncached engineeringband,max6.318466M. ATT40 remains bestvalidreference. 8K with startup-budget fix has not been tested; assess smaller-stage blocking/capacity tradeoff at unchanged6M schedule. No6Mcapacityceiling established. Only three Prefill args change; exact render/rollback saved. Fresh6canonical+4affinity+400warmup precede full11842 measured requests.

### 2026-09-13T21:19:35.066977+08:00 — ATT41 published; secondary controls prepared

Public ATT41 evidence verified at commit 9f5c926dede5f506213f1fd2f785edf4af37aead, HTML SHA256 bd4c2db2226afb1d2b3543d9cbee42e6cc3c3389851e375eba13497f08ff1102; 119 artifact hashes and desktop charts verified. ATT42 rollout has an observer retry for an old deleting Prefill; no serving error conclusion from that administrative termination. Secondary control template expects one Prefill, both Decode nodes, 87 idle gauges and all eight Decode flush confirmations. Source-based leads for Decode KV residency and graph48 versus slot96 are retained; neither is yet an observed long-output bottleneck.

### 2026-09-13T21:25:34.226642+08:00 — ATT42 full confidence gate passed; warmup active

All eight pods ready after505.385s from successful apply; only two Prefills replaced. New P132 UID670c2262-2826-4190-aa25-4d55a8d46bb0; P151 UID19ae8bef-ac68-4afb-93ad-f14034dba773. Both use8K graphs and startup budgets PP0/1=8910624522,PP2=7805586636,PP3=7480108646 bytes, previous values unset. Source/rank/capacity and defaultfraction checks passed, six canonical retrieval checks and four affinity checks passed, exact18048-token cross-Prefill L3 reuse verified. Full cache reset confirmed all eight Decode ranks. Warmup20260913_132423 started; full performance verdict pending.

### 2026-09-13T21:44:33.953898+08:00 — attempt42-two-prefill-8k-startup-budget fulltrialclosed

20260913_132716:11842success/0failure;generatorinvalid;TTFTP50/P992.933608/5.658676s,worst20sP504.385677s,32/603windows>=4s. Load/cachebandsTrue;primarytrialacceptanceFalse. Samecandidate8source,8192chunks. All115gaugesidle,collectorsjoined,source/incarnationschecked. Exactrecipeandrollbackin`attempt42-two-prefill-8k-startup-budget/REPORT.md`.

### 2026-09-13T21:45:00.157752+08:00 — ATT43 6K startup-budget test selected

ATT42 full run is generator INVALID: lag54.661ms exceeds50ms. All11842 succeeded;32/603 windows>=4s,worst4.385677s,globalP50/P99=2.933608/5.658676s; all42621 load/cache engineering-band states pass. No accepted speedup claim. ATT40 remains best valid reference. PP0 observation-counter means indicate shorter8K stages but higher queueing than10K/12K; these are not matched request cohorts or additive decomposition. Test untried6K startup-budget recipe at unchanged6M schedule for this tradeoff. No6Mcapacityceiling established. Only three Prefill args change; exact render/rollback saved. Fresh6canonical+4affinity+400warmup precede full11842 measured requests.

### 2026-09-13T21:52:23.508940+08:00 — ATT43 startup failure before traffic

P151 PP3 Mooncake EGM HOST_NUMA allocation failed; container restarted once automatically. Previous logs and exact old/current IDs retained under`attempt43-two-prefill-6k-startup-budget/rollout/startup-incident`. One unchanged recovery attempt observed; no correctness or performance acceptance.

### 2026-09-13T22:19:20.205043+08:00 — ATT43 closed

20260913_140451:10140success/0failure,1702neveradmitted,validgenerator;TTFTP50/P995.287307/16.399969s,310/529windows>=4s,worst15.653466s. Guard stopped sustained Prefill backlog. All queues idle and collectors joined. FirstP151 EGM allocation failure/automatic one-restart recovery retained. See `attempt43-two-prefill-6k-startup-budget/REPORT.md`. No6Mcapacity ceiling claim.

### 2026-09-13T22:20:29.116510+08:00 — ATT44 diagnostics selected

ATT43 severe backlog at6K:guard-stopped10140success/0failure,1702neveradmitted,validgenerator,310/529windows>=4s. ReturnbestvalidATT40 10K for diagnostics. No6Mcapacity ceiling established. Two Prefills only:6K→10K args/graphs; built-in device timer and opt-in allocator reporter source/env/immutableCM. Six other pods and eight performance candidates unchanged. Fresh6canonical+4affinity/nativecoverage gates; exactrecipe/rollback preserved. CUDA-event interval includes stream/enqueue gaps; allocator counters omit allocations outside its backend and may add overhead. Missing counters are not zero. No native coverage or overhead validation yet; any useful optimization requires uninstrumented confirmation.

2026-09-13T22:38:36.349916+08:00:ATT44 measured20260913_143815 started;full600s C05/output20,diagnostics only. Fresh6canonical+4affinity+400validwarmup pass;all8nativeforward/allocator counters present. Warmup interval had15 allocator retries across8ranks,zeroallocatorOOM; not yet a measured TTFT cause. Two newPrefills restart0;exactbindings archived at arm/runtime-bound.json.

### 2026-09-13T22:54:48.094638+08:00 — attempt44-two-prefill-10k-timing-allocator fulltrialclosed

20260913_143815:11842success/0failure;generatorvalid;TTFTP50/P993.031778/7.101334s,worst20sP506.186856s,79/603windows>=4s. Load/cachebandsFalse;primarytrialacceptanceFalse. Samecandidate8source,10240chunks. All115gaugesidle,collectorsjoined,source/incarnationschecked. Exactrecipeandrollbackin`attempt44-two-prefill-10k-timing-allocator/REPORT.md`.

2026-09-13T22:59:14.343846+08:00:23:00review—ATT44archived/public; primaryremainsPrefillqueuecapacity. BoundednativevalidationselectedbeforepreparedMQAlifetimecandidate;noCUDAprocessyet.19GiBfreeonowned151GPU1,otherPdevicesexcluded;freshidle/source/headroomgatesrequired. SecondaryRS/originaloutputsreadyoffline;02:00slotcheckpointretained. No6Mcapacityceiling/fallback/PRwork.

2026-09-13T23:08:48.436445+08:00—ATT45prepared only: ninthperformancecandidate, consumedMQAscorereferencerelease; unchangedATT44diagnostics/C05/10K.24nativecases/2graphchecks qualified; exactninepatch reconstruction5files. No servingbenefitclaimed.

2026-09-13T23:17:22.250209+08:00 — ATT45 unconditional release remains unapplied: longK PAGED mismatch; fixed-score baseline control reproduces selected-set variation. Separate RAGGED-only revision planned, preserving original PAGED branch. Native06/07 retained.

2026-09-13T23:19:22.503566+08:00—ATT46prepared only: ninthperformancecandidate, consumedMQAscorereferencerelease; unchangedATT44diagnostics/C05/10K.24nativecases/2graphchecks plus6longRAGGEDcases/1graphcheck qualified; PAGEDbranchunchanged; exactninepatch reconstruction5files. No servingbenefitclaimed.

2026-09-13T23:26:27.683013+08:00 — ATT46 applied: RAGGED-only lifetime source182f5b863e82b3075f7ecf3dadf15047f283a967874b80be905f46a8822ce841; native24small+6longK cases and3graph checks passed, PAGED AST/lifetimeunchanged. FirstHelmreleaseSecret exceeded1MiB; failedattempt preserved and liveDGD/source/values unchanged verified. Excluding tests and2unusedchartfiles produced byte-identical render; same planned upgrade succeeded15:22:10UTC. All other6podincarnations retained. No performanceclaimbefore rollout/checks/replay.

### 2026-09-13T23:53:13.185384+08:00 — attempt46-two-prefill-ragged-logits-lifetime fulltrialclosed

20260913_153855:11842success/0failure;generatorinvalid;TTFTP50/P992.980194/5.203011s,worst20sP504.312874s,31/604windows>=4s. Load/cachebandsFalse;primarytrialacceptanceFalse. Recorded9performancecandidates,10240chunks. All115gaugesidle,collectorsjoined,source/incarnationschecked. Exactrecipeandrollbackin`attempt46-two-prefill-ragged-logits-lifetime/REPORT.md`.

2026-09-13T23:55:40.203104+08:00—ATT47prepared only, removePrefilldiagnostics, same9performancecandidates/10K/C05/output20. ATT46closed11842successbutgeneratorinvalid and31/604TTFTwindowsfail. Prior442filearchiveverified. No6Mfallback orsecondaryactivation.

### 2026-09-14T00:31:05.517331+08:00 — attempt47-two-prefill-ragged-uninstrumented fulltrialclosed

20260913_161656:11842success/0failure;generatorvalid;TTFTP50/P992.885089/5.202355s,worst20sP504.135897s,16/603windows>=4s. Load/cachebandsTrue;primarytrialacceptanceFalse. Recorded9performancecandidates,10240chunks. All115gaugesidle,collectorsjoined,source/incarnationschecked. Exactrecipeandrollbackin`attempt47-two-prefill-ragged-uninstrumented/REPORT.md`.

2026-09-14T00:36:02.328152+08:00 — ATT48 prepared, not applied: tenth candidate compact RAGGED MQA logits, source2ca8ca1e5616b140343c95126ad7dbb20d716974edfaad86c0c760795a0668a6. Native02 passed24RAGGED+8ABI+4smallPAGED+20graphreplays; native01 declined headroom before execution. Exact ten-candidate five-file reconstruction; other six serving pods unchanged. Fullmodel and performance gates pending.

### 2026-09-14T01:08:16.717645+08:00 — attempt48-two-prefill-compressed-logits fulltrialclosed

20260913_165356:11842success/0failure;generatorvalid;TTFTP50/P992.886835/5.468581s,worst20sP504.531822s,23/602windows>=4s. Load/cachebandsTrue;primarytrialacceptanceFalse. Recorded10performancecandidates,10240chunks. All115gaugesidle,collectorsjoined,source/incarnationschecked. Exactrecipeandrollbackin`attempt48-two-prefill-compressed-logits/REPORT.md`.

2026-09-14T01:10:49.594653+08:00 — ATT49prepared8Kcompactchunktrial; ATT48closedvalidgenerator/loadbut23windowsover4. Exact3argumentdelta, unchangedtensources. ATT47bestvalidretained; nofallback.

### 2026-09-14T01:25:58.925556+08:00 — ATT49 ready; secondary analysis prepared

ATT49 all8ready in491s,6canonical+4affinitypassed with crossPrefillL3reuse; allrankcache reset done; warmup20260913_172444 active. ATT48publicreport exactbytesverified atcommitf09184c885069c48013b0a1df798a77e364926e6,178artifacthashes. Secondary stillprepared only; original-output analysis recomputes all602ATT28chartwindows exactly, actualoutputs4–20,total117904. Firstchecker incorrectly assumed every output==20; retained/fixed withoutservingmutation. Baseline-derived chunks/graphs andsevenpodDGD/5921terminalhelpers retained under`secondary-1p1d-12gpu/control-template/`. 9Kcompactoptionpreparedonly, notselected.

### 2026-09-14T01:45:30.212437+08:00 — attempt49-two-prefill-8k-compressed-logits fulltrialclosed

20260913_172724:11842success/0failure;generatorinvalid;TTFTP50/P992.855329/5.207214s,worst20sP504.345156s,19/603windows>=4s. Load/cachebandsFalse;primarytrialacceptanceFalse. Recorded10performancecandidates,8192chunks. All115gaugesidle,collectorsjoined,source/incarnationschecked. Exactrecipeandrollbackin`attempt49-two-prefill-8k-compressed-logits/REPORT.md`.

2026-09-14T01:46:42.619174+08:00 — ATT50prepared9Kcompactchunktrial; ATT49closedinvalidgenerator/loadbandfailand19windowsover4. Exact3argumentdelta, unchangedtensources. ATT47bestvalidretained; nofallback.
