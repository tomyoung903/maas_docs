# ATT37 — unchanged 10K diagnostic: DSA logits splitting lead

Measured Alex run: [20260913_102428](http://43.156.43.133:31019/replay/runs/20260913_102428/report?view=overview&columns=overview). Warmup: 20260913_102110. **Interrupted negative diagnostic: 4,212 successes, zero failures or empty outputs, 7,630 never admitted.** The existing guard stopped admissions with frontend active 280 and Prefill queue 231 after its sustained backlog threshold. Last body upload t=213.036368s; last completion t=227.256409s. No full 600s performance pass is claimed.

## Result

Whole client TTFT p50/p90/p99: **8.797097 / 15.531048 / 17.048028s**. Every one of 227 Alex trailing 20s completion-window points was independently reconstructed; **166 exceeded 4s p50**. Worst p50: **14.228924s at t=141**, 383 samples. Generator lag p99 was **52.171902ms**, above the unchanged 50ms ceiling; source admission p99 27.717090ms and body-send p99 33.458246ms passed their separate limits. This instrumented, interrupted trial is diagnostic regardless of those checks. The lighter status observer is not proven to fix generator lag.

Input 213,264,716; cached 191,791,936; uncached 21,472,780 tokens. Cache hit **89.931396%**; boundary approximation over the admitted span: 60.064M input / 6.048M uncached TPM. Net finite-plan cache deficit 149,632 tokens. Full 60s demand windows are audited only within the partial admission span. Store recorded 13 eviction passes and 818,460,751,872 cumulative evicted bytes through closure. All request identities match the candidate05 prefix.

## Unchanged runtime and observation changes

All eight pod/container identities, serving source/images/resources/topology and 10K Prefill arguments remained fixed from ATT36. Same candidate05, output20, affinityTTL1800, projected-load escape0, KV capacities and 1300GiB Store. The six optimizations plus producer-event wait remain the seven retained serving changes; no eighth serving patch was applied.

Canonical six and affinity four checks were explicitly inherited from the identical ATT36 runtime. Fresh generator/dataset/token attestations passed; a fresh scoped KV reset covered both Prefills and all eight Decode DP ranks. Warmup completed 400/400 with zero failures and a valid generator; its cold-cache TTFT p50/p99 were 20.140877 / 27.623547s. These warmup values are separate from measured acceptance.

The repeat began inside the prior session idle TTL. An interim exact native-log join found all 2,148 overlapping completed requests retained both worker identities. That interim result is not coverage of the unobserved tail; the full overlap audit is retained separately when completed. The distributed Decode ID does not expose its DP rank.

Added observer: nonblocking Python CPU-stack sampling at a requested 2Hz for 120s on all eight Prefill scheduler processes, starting after t=30. Exact pod/container IDs, scheduler PIDs, process birth ticks, commands and source hash were bound. No GPU tracing or serving hooks were used. ATT36's separate Alex OS sampler was not repeated; this is another observation difference.

## Profile finding and limits

Seven profiles completed with 213–224 main-thread samples each, 15–26 reported read errors per process, and measured command intervals approximately 110–134s despite requested 120s sampling. Nonblocking sample proportions and synthetic thread weights do not establish wall-time attribution. Native stacks were not captured.

The P151 PP0 sampler exceeded the 155s local command limit and remained alive remotely. Exact command/birth checks identified only the owned sampler PID3448. SIGINT did not exit within 30s; SIGKILL then stopped that sampler, verified gone or zombie. No PP0 profile was recovered. The serving PID706 was not signaled. Original timeout, graceful-stop failure, forced-stop receipt and seven successful profiles are preserved. This missing profile is not treated as a successful eighth capture.

On P151 PP1, **131/222 main-thread samples** were inside `_get_topk_ragged`'s logits subchunk loop; P132 PP1 had **2/213**. P151 PP2/PP3 had 127/224 and 152/220 samples in PP communication waits. P132 commonly sampled allocator `torch.unique` or page-map synchronization instead. Breakable CUDA graph replay explicitly includes eager DSA split operations, so a `cuda graph: True` batch does not imply the complete indexer is captured.

All four relevant active DSA source files were exported from both Prefill pods and match their frozen hashes. `dsa_indexer.py` caches its MQA logits budget from the first non-capture free-VRAM reading, capped by static serving headroom; later chunk sizes reuse it. This is a concrete mechanism worth investigating. **Actual cached budget values, per-batch split sizes and a causal benefit from changing them have not yet been observed.** Transient allocator state or different first-use memory readings remain hypotheses. No budget increase or OOM guard relaxation has been made.

## Closure and reproduction

All 115 queue gauges were idle in two checks; all identities and retained per-role source hashes matched. Every collector was joined and the remaining owned sampler was forcibly closed as documented. Twelve lower-tier removal warnings and zero frontend ERROR events occurred in the watcher interval. TPOT remains deferred: 15 requests above40ms, four above80ms; 20 windows above40ms p99.

Recipe: `chart/`, `preparation/`, `rollout/UNCHANGED.json`. Closure: `replay/evidence/DRAINED.json`. Raw timing export/checksum: `../evidence/20260913_102428/`. Reconstructed chart: `../evidence/latency-comparison-20260913_102428-partial.json`. Load and Store: `replay/workload-analysis.json`, `rolling-load-cache-audit.json`, `evidence/store-counter-deltas.json` under replay. Profiles, quality and timeout recovery: `cpu-stacks/`; source at execution: immutable local `capture_prefill_cpu.py`. Source verification and lead: `evidence/dsa-active-source/VERIFIED.json`, `evidence/DSA-SPLIT-LEAD.json`.

Next: inspect numeric logits budgets and split dimensions in a bounded diagnostic while retaining current memory-safety limits. Only then choose a controlled fix. Primary acceptance remains a valid, uninstrumented, full 600s candidate05 test with zero errors and every Alex 20s TTFT p50 below4s.
