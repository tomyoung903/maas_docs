# ATT39 — startup-budget candidate deployed; warmup only

This milestone records a completed source rollout and bounded validation, **not a full measured performance result**. The user paused after warmup; no measured replay was launched. Warmup Alex run: [20260913_112533](http://43.156.43.133:31019/replay/runs/20260913_112533/report).

## Source change

One opt-in scheduler hook initializes/refreshes the cached DSA MQA logits budget after graph capture, optional KV resizing and weight-load finalization, before dispatch. It uses the unchanged original getter and its0.2 free-memory fraction/static memory guard. It runs only for the CUDA Prefill target worker; no per-request memory query, arbitrary budget increase or allocator cache clearing was added. The existing seven scheduling/publication/producer-event changes are retained.

Candidate `candidate/startup-budget.patch`: SHA256`ea6cc26332dd13f58caf2275aabd7a10382d1e123f60a35bd83be2581754c67f`. Patched scheduler SHA256`85bbce778a5683b013c54824e29eef2119fcde27e50c8954183f7e9fe00bf63d`, frozen original`9080391af1f994b1a975347d038ef3f9fec2c31338d354a6ec2dba791d63ced0`.

Complete seven retained changes plus candidate: `preparation/complete-eight-candidate-against-frozen.patch`, SHA256`48a16944ecb09fea4b2dca5d7e8520ca8c5821ad7f54a51981c2d1f8ef0e884c`. All four changed files reconstructed exactly against frozen SGLang6d08e28b0c0691899973e3f11bf01fdbdf192a63. Other pre-existing overlays/images remain dependencies. No production merge.

## Startup and checks

Only two Prefill pods rolled; Decode, frontend and three Store pod incarnations remained unchanged. Source/image identities, PP4/TP1 Prefills, distributedTP8/DP8 Decode, all KV capacities and1300GiB Store were verified. All eight Prefill ranks logged an unset prior cache at the hook, then initialized corresponding-rank budgets identically on both nodes: PP0/PP1=8,910,624,522bytes; PP2=7,564,414,156; PP3=7,269,554,585.

This directly observes initialization before serving on the new incarnations; it does not show when ATT38's old88MB value was initialized. For ATT38's captured10,077-query/538,333-key dimensions, the newPP1budget would permit3splits instead of252. That is arithmetic, not observed ATT39 batch timing or a speedup claim.

Eleven CPU contract tests passed. Six canonical retrieval checks passed, with exact18,048-token cross-Prefill L3 reads on each of fourPP ranks in both directions and actual10Kgraph replay. Four session-affinity checks passed, including DecodeDP0/DP4 on the two physical nodes. This is bounded verification, not general model-correctness proof.

The fresh cache reset flushed both Prefills and all eight DecodeDP ranks. Dataset/token/generator hashes matched. The400-request warmup completed without failures or empty outputs, with valid generator lagp995.865741ms. Cold warmup TTFTp50/p99=17.183700/22.487561s; duration128.462311s. This cold warmup does not test the primary60M/6M steady workload.

## Closure and reproduction

User pause followed warmup; all collectors were joined and115queuegauges verified idle twice. Resumption reverified the same runtime, no active Alex replay, idle queues and every retained per-role source hash. The pause exceeded routing idleTTL1800s, so the next measured attempt must receive a distinct directory and fresh cache/warmup. Preserve this original checkpoint.

Recipe and rollback: `preparation/`, `chart/`, `rollout/INTENT.json`, `rollout/APPLIED.json`. Candidate and CPU tests: `candidate/`; reconstruction: `preparation/COMPLETE-PATCH-VERIFIED.json`. Startup budgets: `evidence/STARTUP-BUDGETS.json`, `GETTER-SOURCE-VERIFIED.json`, `INITIALIZATION-OBSERVATION.json`. Bounded checks: `correctness-01/`, `affinity-correctness/`, and their closure receipts under`evidence/`. Warmup: `replay/warmup-*.json`; pause: `evidence/USER-PAUSED.json`; final warmup-only closure: `replay/evidence/DRAINED.json`.

Local preparation initially assumed the chart appended the opt-in environment variable last; exact named removal fixed that assertion, with the failed preparation preserved. A later receipt command omitted its required arm argument; the successful runtime binding was retained, and only the missing receipt/dependent audit was rerun. Both were local setup errors before benchmark traffic and are recorded separately from serving results.
