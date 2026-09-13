# ATT43 — 6K chunks caused a sustained backlog; partial negative result

Alex: [20260913_140451](http://43.156.43.133:31019/replay/runs/20260913_140451/report?view=overview&columns=overview). **10,140 successes, zero failures/empty outputs, 1,702 never admitted.** Generator **valid**. The planned600s C05 trial was stopped by its existing guard: frontend active>=250 and combined Prefill queue>=120 sustained15s. At stop:306 active,266 queued; Decode partition stage counts30–43, below the80 guard. Last body upload t=513.664474s; last completion t=529.992905s. This is not a full-run qualification.

## Latency and load

Completed-request TTFT P50/P75/P90/P99 **5.287307/7.287501/11.679694/16.399969s**. All529 Alex trailing20s completion-window points were independently reconstructed. **310/529 windows>=4s**, worst **15.653466s at t=530.0**,372 samples. The worst window lies in drain; it is retained. These windows use completions, unlike live last200-request estimates or admission-minute cohorts.

Generator lagp99 35.926886ms, admissionp99 33.037270ms, body-sendp99 40.669469ms; zero connector waits. Original thresholds unchanged. All admitted identities match the C05 plan prefix.

Input514,010,827; cached462,025,472; uncached51,985,355; hit89.886331%. Net finite-plan excess611,584tokens. All35,809full60s admission-window states within the actual513.664s span passed59.4–60.6M input/5.7–6.3Muncached engineering bands. These are demand checks, not physical GPU throughput or full600s acceptance. Store39 eviction passes, cumulative2,453,979,601,920bytes evicted.

Shorter PP0 bootstrap/forward/handoff counter means accompanied much larger queue times. Stage/cache observations are in `evidence/affinity-stage-cache-600s.json`, with ATT43 clipped to510s and actual scrape offsets retained. Counters are not matched request cohorts or additive latency decomposition. The test rejects6K as an improvement in this recipe; it does not prove6M unattainable.

## Startup incident retained

First Prefill151 container failed before any benchmark traffic: PP3 DSAIndexerPoolHost EGM allocation logged `cuMemCreate failed with CUDA result 2`, followed by the parent's SIGQUIT handling. Kubernetes reported the exited parent as exit0/Completed despite the fatal child. Previous-container logs, pod/events and memory evidence remain in `rollout/startup-incident/`.

Kubernetes automatically restarted the same pod once. An exact UID/container/restart1 recovery intent allowed that one observed replacement; no manual cache reclaim, compaction, additional restart or configuration change was performed. Prefill132 had zero restarts. Both then passed fresh rank/graph/source/capacity checks, all eight startup-budget logs, six canonical and four affinity checks, and400/400 valid warmup requests. Apply-to-ready took706.780702s including the failed first startup. The later memory snapshot is not the failure-time state. The allocation failure's root cause is unproven and cannot be attributed to6K from this evidence.

## Recipe and closure

Only Prefill chunk/max-prefill/graph sizes changed8192→6144; two new Prefill incarnations, six other pods unchanged. Same eight retained performance candidates, images, resources, L2/L3 capacities, strictaffinity1800/escape0, C05/output20. Default MQA free-memory fraction remains0.2. No device timer or allocator observer was active. A read-only source-file audit prepared later diagnostics without Torch imports or CUDA calls. Rejection sampling remains prepared for the later12GPU1P1D trial and was not enabled here.

All115 queue gauges idle in two checks, all collectors joined, exact bound identities and serving source hashes rechecked. Frontend watcher: zero ERROR events,57 lower-tier warnings; truncated tool-call warnings retained separately with output20 context. Partial TPOTp99 19.254770ms;26 requests>40ms,12>80ms,55 windows withp99>40ms. TPOT spikes remain deferred, with no full contract certification or general KV correctness guarantee.

Exact recipe/rollback: `chart/`, `preparation/`, `rollout/INTENT.json`. Complete eight-candidate patch and reconstruction receipt: `preparation/`. Startup/recovery: `rollout/startup-incident/`, `rollout/READINESS-TIMING.json`. Accounting/guard/drain/load: `replay/`. Timing export: `../evidence/20260913_140451/`; partial reconstruction: `../evidence/latency-comparison-20260913_140451-partial.json`. Archive receipt follows under `../milestones/attempt43-two-prefill-6k-startup-budget/`. Raw request bodies and private logs are excluded from public reporting.

Next: return to the best valid10K recipe with bounded Prefill device-time and allocator counters to identify the next optimization. Both are diagnostics with possible overhead; any resulting performance change requires an uninstrumented confirmation. No fallback load or PR work has started.
