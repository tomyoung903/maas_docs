# ATT34 — all requests completed; generator invalid and TTFT windows fail

Alex measured run: [20260913_084212](http://43.156.43.133:31019/replay/runs/20260913_084212/report?view=overview&columns=overview). Warmup: 20260913_083932. The measured schedule ran for the full 600 seconds: all 11,842 requests succeeded, zero failures, zero empty outputs, no backlog/failure guard stop. However, Alex's final state is **invalid_load_generator**. Event-loop lag p99 was **50.389651ms**, exceeding its existing 50ms ceiling. Admission-delay p99 37.372969ms and body-send-delay p99 47.116749ms passed their separate 50/100ms limits; connector queue events were zero. Do not override or round away the invalid label. This arm supplies diagnostic evidence, not accepted performance.

## Change and exact reproduction

Only the two Prefills changed from ATT33: chunked-prefill-size and max-prefill-tokens 8192 → 12288, with 12288 added to the breakable Prefill CUDA-graph sizes. Both Prefill pods rolled; all six other pod/container identities remained unchanged. No serving source code, container image, frontend setting, Decode setting, Store capacity or dataset changed. Both new Prefills captured the intended 12K graphs on all four PP ranks. Their GPU KV capacity remained 9,252,096 tokens per rank; Decode remained 3,135,616 per rank.

Topology: PP4/TP1 Prefill132 and Prefill151, with one TP8/DP8/EP8 Decode across 130 and192. Prefill async depth1 and the six optimization overlays plus producer-event wait remained. Frontend session-affinity TTL1800s and projected-load escape0 remained. Private Mooncake Store stayed 2×650GiB. Complete charts, before/trial values, rendered scope diff and rollback command are in `chart/` and `preparation/`; actual runtime identities/source hashes are in `runtime-bound.json` and `evidence/runtime-attestation.json`.

Six canonical cold/shared/cold retrievals and four affinity checks passed before the fresh scoped reset. All shared retrievals verified the four PP ranks; Decode checks covered DP0/DP4. These are bounded regression checks, not comprehensive correctness validation. Fresh reset verified all eight Decode DP ranks and both Prefills. Warmup sent 400 requests over a separate 120-second schedule, all successful. Its cold-cache TTFT p50 was 16.931308s and p99 21.832630s; those high warmup values remain recorded separately from the measured run.

The measured workload is unchanged candidate05: dataset `dataset-ff27e5775a3fafe07c306868`, token profile `profile-4af517c7667ceb975392f966`, 11,842 real requests/600s, output cap20, concurrency ceiling1024. Exact schedule, source identities, prepared token sequences and payload-store hashes were verified. The CPU generator pod, container, image and source stayed fixed. Last body upload was at t=599.962058s and last completion at t=603.728799s.

## Observed latency and demand

Whole-run TTFT p50/p90/p99: **3.345125 / 4.565064 / 5.803573 seconds**. All 603 Alex trailing20s chart points were independently reconstructed from raw completion timestamps. **56 windows exceeded four-second TTFT p50**; worst **4.571117s at t=457**, 390 samples. The corresponding ATT33 values were 213/603 windows and 6.115510s. This is a promising observed difference, but generator invalidity prevents treating it as a clean validated improvement. The primary TTFT target fails independently of that invalidity.

Actual input600,333,408, cached539,549,760, uncached60,783,648 tokens: **89.875018% hit**, approximately **6.078M uncached TPM** over the600s schedule. Net deficit versus the finite plan was779,264 tokens. All admitted identities exactly matched the candidate05 schedule. Server/local input differed by305 tokens overall.

All42,621 distinct boundary/interior states of full60s admission windows were audited. Offered input ranged59,746,716–60,258,975 tokens; actual input59,746,746–60,259,002; actual uncached5,935,560–6,291,694. All stayed within the recorded engineering bands of ±1% input and ±5% uncached. These are eventual server outcomes grouped by body-upload time, not instantaneous physical compute throughput. Passing demand bands does not override the invalid generator.

## Queue, cache and remaining hypotheses

Early PP0 counters show the tradeoff: 12K chunks reduced Prefill waiting while increasing forward, bootstrap and handoff time per request. In the first120s, ATT34's two Prefills averaged approximately0.46/0.40s waiting versus ATT33's1.26/0.55s. Forward rose to approximately1.05/1.04s from0.83/0.78s. These are observation-time counter means, including readiness, not matched-request or additive TTFT decompositions. Full600s stage and GPU/host/Store token counters are retained in `evidence/affinity-stage-cache-600s.json`, with actual scrape offsets.

From measured baseline through terminal idle, Store recorded47 successful eviction passes,6,697,247 evicted objects and2,958,745,057,536 evicted bytes. Allocated bytes changed837,775,471,104→1,205,394,779,904; total capacity remained1,395,864,371,200. Cumulative eviction counts churn and is not unique working-set size. The entire saved frontend interval contained52 lower-tier-index warnings, all “Failed to find block”; ATT33 had similar warnings. Inspected frozen native source emits this error on removal of an absent worker/block. The available warning fields do not identify the affected block or establish a KV fetch failure. No frontend ERROR events were recorded.

TPOT remains deferred by Tom's priority: whole p99 19.149939ms; worst20s p99 150.708568ms at t=385;35 requests above40ms and28 above80ms. Keep these measurements without expanding standalone TPOT or correctness work unless they block 2P1D TTFT.

## Closure and next action

All115 engine/frontend queue gauges were idle in two terminal checks. All eight pod/container identities and expected per-role source hashes matched after the run. Collectors and guards were stopped and joined; `tool-sessions.json` has no active sessions. `replay/evidence/DRAINED.json` preserves closure and marks acceptance false.

Next: repeat the unchanged12K configuration with fresh cache, the same warmup and exact workload. Keep the existing generator validation threshold. Establish a valid repeat before deciding between an intermediate chunk size and cache-aware scheduling. No new serving change has been applied for that repeat.

## Evidence and setup incidents

- Raw timing exports/checksums: `../evidence/20260913_084212/` and `../evidence/20260913_083932/`.
- Exact603-point reconstruction: `../evidence/latency-comparison-20260913_084212.json`.
- Full identity/load/cache accounting: `replay/measured-events-slim.jsonl`, `workload-analysis.json`, `rolling-load-cache-audit.json`.
- Runtime logs, five-second metrics, node samples, guard records and closure: `replay/`; Store deltas and structured frontend warnings: `replay/evidence/`.
- An early binding invocation found the readiness receipt missing and exited locally before remote action; preserved in `evidence/bind-premature-gate.json`. It was retried after both Prefills were Ready. No runtime restart/OOM occurred.
- Alex finalized the report after the request stream drained. The final invalid-generator label was incorporated immediately; interim live progress was never final acceptance.
