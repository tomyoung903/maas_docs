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
