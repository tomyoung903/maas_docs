# ATT38 — cached MQA logits budget observed

Alex measured run: [20260913_104049](http://43.156.43.133:31019/replay/runs/20260913_104049/report?view=overview&columns=overview). Warmup: 20260913_103743. **Interrupted numeric diagnostic; 2,715 successes, zero failures/empty outputs; 9,127 never admitted.** Manual stop followed acquisition of the bounded diagnostic, not a backlog-guard trigger. Last body upload t=137.262803s; last completion t=146.396412s. No full 600s performance result is claimed.

## Finding

One internally coherent nonblocking local-variable snapshot on Prefill151 PP1 showed a cached logits budget of **88,067,276 bytes (83.987499 MiB)**. A 10,077-query, 538,333-key ragged indexer batch required 2,153,332 bytes per query row. The budget allowed only 40 rows per internal split: **252 subchunks**, instead of a single 21,699,126,564-byte logits allocation. This establishes excessive splitting in that captured batch, not its wall-time share or a proven remedy.

Two other numeric snapshots contained stale/inconsistent locals and are explicitly excluded. No numeric budget was captured on Prefill132; absence is not zero. Both PP1 probe parents completed, all 24 dump children exited zero, and none timed out. Raw locals remain private because they can contain request data. Only numeric allowlisted fields are suitable for public reporting.

Active DSA files match frozen source on both Prefills. The getter caches its first non-capture free-VRAM budget, with the existing static headroom cap. Actual free-memory fraction is the default **0.2**, with no environment override in either scheduler process. The source's older comment about a half-memory guard does not override this value. The 88 MB budget's original initialization time and transient allocator state were not observed.

Next candidate: refresh this cache once after worker startup allocation/graph capture, through the existing getter and unchanged free/static guards, before serving traffic. This is a hypothesis to test. No serving source was changed in ATT38.

## Latency, load and finite cache

Client TTFT p50/p90/p99: **4.813743 / 9.346102 / 10.852786s**. All 146 Alex trailing20s completion-window points were reconstructed; **70 exceeded four seconds p50**. Worst p50 **9.071468s at t=137**, 361 samples. Generator valid: heartbeat lag p99 **21.383500ms**, admission delay p99 **26.222761ms**, body-send delay p99 **31.939611ms**, zero connector waits. These checks do not make an instrumented partial run a performance pass.

Input137,551,272; cached123,719,872; uncached13,831,400 tokens; hit **89.944550%**. Net finite-plan cache deficit89,920 tokens. All6,109 full60s demand states within the partial admission span passed the recorded engineering bands around60M input/6M uncached. Whole-prefix span approximation60.126M/6.046M TPM; Alex's final-request-excluding input estimate60.057M TPM uses a different boundary convention. Store recorded six eviction passes and377,558,487,552 cumulative evicted bytes through closure. These are partial-span observations only.

TPOT remains deferred: whole-run p9918.730083ms; ten requests>40ms/four>80ms; twenty windows>40ms p99, worst81.304201ms. This is not a TPOT qualification.

## Reproduction and closure

Same eight pod/container incarnations and10K arguments as ATT36/37; same candidate05, output20, affinity1800/escape0, seven retained source changes and fixed resource/cache capacities. Six canonical and four affinity checks were explicitly inherited from identical runtime. Fresh dataset/generator/token attestation and scoped KV reset preceded400/400 successful warmup requests with valid generator; cold warmup TTFT p50/p9920.402609/28.407322s. Session bindings were retained within their idle TTL; KV reset does not clear those bindings. No full measured-placement join is claimed.

Observation change: only two PP1 processes received12 bounded nonblocking locals dumps each after45s, with2.5s child deadlines and guaranteed child kill/join. ATT37's all-rank CPU sampling was not repeated. An inherited warmup note mistakenly mentioned that older sampling; the measured note was corrected before launch and both original note and correction are preserved. Actual executed probe source is frozen locally at `probe_logits_budget.py`.

All2,715 admitted identities match the candidate05 prefix. All115 queue gauges were idle in two closure checks; all bound incarnations and retained serving sources matched; all collectors joined. Twelve lower-tier removal warnings and zero frontend ERROR events occurred in the full watcher interval. Parser truncation warnings are separately retained with output20 context.

Recipe: `chart/`, `preparation/`, `rollout/UNCHANGED.json`. Numeric finding: `evidence/LOGITS-BUDGET-FINDING.json`; environment proof: `evidence/mqa-fraction-env.json`; raw private probes and exit receipts: `numeric-probes/`. Manual stop receipts: `replay/evidence/numeric-diagnostic-stop*.json`. Closure: `replay/evidence/DRAINED.json`; accounting/load: `replay/workload-analysis.json`, `rolling-load-cache-audit.json`, `evidence/store-counter-deltas.json` under replay. Raw timing export: `../evidence/20260913_104049/`; reconstructed chart: `../evidence/latency-comparison-20260913_104049-partial.json`.

The primary goal remains a valid, uninstrumented full600s candidate05 run with zero errors and every Alex20s completion-window TTFT p50<4s. Seven retained source changes are experimental overlays, not merged production code. New startup-budget work is not yet applied or validated.
