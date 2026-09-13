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

| ATT35: unchanged12K repeat | Prepared with identical eight runtime incarnations; fresh cache reset and generator attestation underway | `attempt35-two-prefill-12k-repeat/preparation/PREPARED.json` |

Latest phase and active process handles: root `STATUS.json` and the current arm's `STATUS.json` / `tool-sessions.json`. An applied configuration is not a completed experiment. Failed and partial arms remain in this table.

Published report: https://tomyoung903.github.io/maas_docs/glm53-gb300-ttft-tpot-optimization/

Closed milestones receive a private archive and verified file manifest under `milestones/`. The archive preserves code/configuration and evidence references; model data, images, credentials and external services remain reproduction dependencies.
