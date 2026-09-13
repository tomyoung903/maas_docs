# ATT54 — interrupted by frontend parser panic; primary target not met

[Alex measured run 20260913_200602](http://43.156.43.133:31019/replay/runs/20260913_200602/report). C05, 60M input/~6M uncached TPM, output cap20, two4GPU Prefills and one8GPU Decode. Admission stopped at439.406319s; lastcompletion443.825203s. **8,675 protocol successes +1failure +3,166 never admitted =11,842 planned**. Generator valid under unchanged50/50/100ms gates. This is a partial trial, not a completed performance result.

## Latency and output coverage

Among8,664 requests with visible generation, TTFT P50/P75/P90/P99 **2.628571/3.315298/4.217049/5.840450s**. Eleven protocol-successful responses reported output20 and DONE but no visible generation timestamps; do not count them as verified meaningful output or impute their TTFT. Alex empty-output counter is0 because it uses server usage. All443 eligible Alex trailing20s completion-window points independently match; **11 exceed4s**, worst4.940247s at441s (374samples). Failing seconds: [434.0, 435.0, 436.0, 437.0, 438.0, 439.0, 440.0, 441.0, 442.0, 443.0, 444.0]. These overlapping windows are not11 independent incidents. The final interval overlaps the parser failure and drain, so causal isolation requires a repaired replay.

Generator event-loop lag P99 36.479501ms; admission 37.566277ms; body-send 46.183795ms; connector waits0. No CPU profiler or compilation ran during measured traffic. TPOT P99 25.216015ms on8,664 eligible requests;32request values>40ms,26>80ms,100chart P99 windows>40ms. No TPOT contract certification.

## Failure and stop chronology

At04:13:09SGT the frontend Rust tool parser panicked at `lib/parser/src/tool_calling/xml/glm47_parser.rs:583:32`: byte12 cut inside the UTF-8 character ď after a leading space. It used the trimmed function-name byte length to slice the original content. The stream returned HTTP200 but incomplete transfer framing, with interim input49646/cache0/output3 and no DONE. The frontend subsequently logged cancellation; this does not establish a client-originated disconnect. No bootstrap rejection, SGLang exception or pod restart was observed. This parser flaw is present in the selected ff778ed source; model output alone does not prove rejection-sampling or KV corruption caused the defect.

The observer detected the client failure and requested owned admission drain at04:13:24, after the panic. All8,676 admitted requests reached terminal accounting. Full private evidence is under `evidence/failure-01/` and `replay/evidence/`; `replay/measured-failure-stop.json` preserves the stop. The runtime log classifier did not match the non-JSON Rust panic; the client-failure guard stopped the run. No serving source was changed during it.

## Load and cache

Successful input439,648,611; cached395,246,016; uncached44,402,595; hit89.900436%; net finite-plan deficit449,536tokens. Approximate successful uncached rate over observed admission span6.063080M; it excludes the failed stream's unknown final usage. All29,951 exact full60s offered-input window states were within±1%. For actual input/uncached demand,28,299 fully known states passed engineering bands and1,652 states are indeterminate because final failed-stream usage is unavailable. Known uncached min/max5,938,826/6,246,935tokens per60s. No full600s acceptance or capacity ceiling follows. Store33evictions,2,076,857,622,528bytes cumulative churn; capacity unchanged1300GiB.

## Setup, qualification and reproducibility

Prefill132/151 uses9K chunks and11 source candidates, including the startup-primed earlier-bootstrap candidate73aaee27. All8PP ranks logged priming complete and active;6canonical plus4affinity checks passed before cache reset. Decode130/192 retains EAGLE3/topk1/draft4 with rejection sampling enabled. Compared with ATT50 both sampling and Prefill source change, so neither receives isolated credit. Warmup20260913_200300 completed400/400 with valid generator; cold TTFT P50/P99 17.303610/23.137751s is separate.

Exact recipes, rendered resources, rollback,11-candidate patch and reconstruction hashes are in `chart/`, `preparation/`, `rollout/`, `bootstrap-candidate/`. Full worker identities/source hashes are in `runtime-bound.json` and `evidence/runtime-attestation.json`. `evidence/affinity-stage-cache-420s.json` contains descriptive same-duration stage comparisons with ATT50; different incarnations, routing, sampling and cache behavior prevent causal attribution. Raw timing export is `../evidence/20260913_200602/`; exact latency result is `../evidence/latency-comparison-20260913_200602-partial.json`.

Post-run115queue gauges idle twice, all collectors joined, bound identities and worker/Store source hashes rechecked. Serving retained. Missing-generation and failed-usage analyzer amendments are preserved alongside original analyzer copies; the prepared full-success closure script was not selected. `evidence/ANALYSIS-PROVENANCE.json` records exact results and input hashes. A verified immutable private recipe/code/evidence archive follows under `../milestones/attempt54-two-prefill-primed-bootstrap-rejection/`. No draft PR created; primary2P1D work continues.
