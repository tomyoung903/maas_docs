# 80K rerun milestones

All times Singapore, 14 September 2026. Original receipts are authoritative for precise timestamps.

| Time | Milestone and acceptance |
|---|---|
| 11:57 | Restored 2P4+D8 deployment Ready. Effective sources/native frontend and actual per-rank pools matched the historical recipe; metadata-master placement exception recorded. |
| 12:17 | Both real-request 80K packs prepared in Alex. Every selected original token sequence and all payload frames verified. Prepare sent no inference requests. |
| 12:20 | 2P warmup started; subsequently 400/400 meaningful successes. Shared Store had been verified empty. |
| 12:23 | 2P measured run `20260914_042326` started: 7,504 requests, 600s admissions, output cap 20. |
| 12:33 | Last 2P response completed at admission elapsed 603.294s. |
| 12:35 | 2P report finalization completed. Full 7,504 protocol successes; 7,500 meaningful outputs. Generator valid; all 603 eligible completion-window TTFT medians below 4s. Full acceptance withheld for missing generation, TPOT tails and live rolling-load/cache departures. |
| 12:37 | Transitioned to 1P4+D8, retaining exact surviving containers. Node 151 released and all four GPUs verified at zero memory/no GPU processes. |
| 12:41 | 1P original-output warmup `20260914_044105` started after all-eight-rank retrieval/rejection checks and a fresh owned-cache reset. |
| 12:55 | Warmup finished: 100/100 meaningful successes, no failures. Original outputs took 830.747s in total; no artificial 20-token cap was applied. |
| 12:55 | 1P measured run `20260914_045518` started: 3,760 requests over 600s, original output policy. Executed dataset/profile and absence of override verified. |
| 13:05 | All 3,760 measured 1P requests admitted within 600s. |
| 13:09 | Last 1P request completed at admission elapsed 851.755s. All 3,760 produced meaningful output; no failures. |
| 13:11 | Final 1P raw analysis and collector closure complete. TTFT P50/P99 3.171/23.110s; 12 admission-window medians at or above4s, worst4.075s; no drain failures. TPOT P99 23.905ms, no request above40ms. Live uncached windows all within±5%; input has a0.062s tolerance departure. |

Both requested reruns are complete. The 1P4+D8 deployment remains allocated on132/130/192; all owned observers are stopped and no further replay is scheduled. `STATE.json` records the explicit retained-resource state.
