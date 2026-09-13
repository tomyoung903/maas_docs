# attempt57-one-prefill-primed-real-output — real-output12GPU trial

Alex: [20260913_215025](http://43.156.43.133:31019/replay/runs/20260913_215025/report?view=overview&columns=overview).

One4GPU Prefill (prefill-132) and distributed8GPU Decode (130/192). Baseline source recipe: `/mnt/HPC/tom/pd-latency-followup-20260913/attempt56-two-prefill-utf8-repeat`. Decode uses `--speculative-use-rejection-sampling`; source, shared vocabulary, startup activation and eight-rank sampling are recorded. The original30M input/~3M uncached dataset and original output caps/absence are preserved. There is no20-token override. Both650GiB Store clients remain, which differs from ATT28's topology/cache context.

## Outcome

5921 successful, 0 failed, 0 empty and 0 unadmitted requests out of5921. Generator: **valid**. Strict20sTTFT windows reaching4s: **2/729**. Worst window p50: **4.080042218789458 seconds**. TTFT/load gate: **False**. Full contract is not certified: OTPS55/30/25 positions among five supplied columns remain unresolved. Normal TPOT/OTPS and threshold fractions are reported; standalone p99-spike investigation is deferred.

Protocol successes without meaningful generation: **0**. Missing timestamps stay missing and prevent whole-request acceptance. Usage-token totals are retained separately.

Whole-run TTFTseconds: `{"count": 5921, "min": 0.9019764605909586, "max": 207.88320129038766, "avg": 3.678836397643663, "p50": 3.0211462429724634, "p75": 3.794863684568554, "p90": 5.126212772913277, "p99": 15.359560633637074}`. Normal request TPOTmilliseconds: `{"count": 5921, "min": 0.0, "max": 72.47226766345126, "avg": 9.439151445982544, "p50": 12.92246807087946, "p75": 17.472601633590575, "p90": 19.77751490711752, "p99": 24.945029885696304}`. Finite per-request OTPStokens/second: `{"count": 3284, "min": 13.798381536008062, "max": 603.7180130331258, "avg": 63.37272404954812, "p50": 58.48891835596686, "p75": 67.16484491575413, "p90": 77.10855164170164, "p99": 177.9420036960773}`. Full distributions and descriptive18/33/40ms fractions are in`replay/measured-original-output-analysis.json`; zero-duration TPOT cases are counted separately. All Alex20s windows were independently reconstructed, including any completion/drain period. Whole-run quantiles alone do not establish the window goal.

## Actual workload and counters

Actual generated output total: **4,060,571**; length statistics: `{"count": 5921, "min": 3, "max": 53924, "avg": 685.7914203681811, "p50": 126.0, "p75": 376.0, "p90": 1470.0, "p99": 9919.400000000016}`. Finish reasons: `{"tool_calls": 5545, "stop": 376}`. Configured caps are not generated lengths. Output normalized by600s admission and by full completion elapsed time is recorded separately: `{"per_admission_second": 6767.618333333333, "per_complete_elapsed_second": 4943.393621676045, "admission_duration_s": 600, "last_completion_s": 821.4136503706686, "basis": "Terminal successful output totals. Admission-normalized and full-drain-normalized rates are distinct; neither is an instantaneous token-rate counter."}`. These are not instantaneous counters.

Known successful cache usage: `{"requests": 5921, "input_tokens": 300255283, "cached_tokens": 270284992, "uncached_tokens": 29970291, "hit_rate": 0.9001839677871712, "missing_usage_successful": 0, "failed_uncached_tokens_unknown": 0}`. Full60s30M/3M engineering load bands passed: **True**. Missing/failed requests prevent a full capacity claim; missing server usage is not converted to zero. See`replay/workload-analysis.json` and the load audit when a complete successful cohort permits it. These are admission-cohort demand checks, not physical GPU throughput.

Tokenizer finished-output counter delta: 4060582.0; completed verify calls: 1524563.0. Scheduler eight-rank decode-token delta: 4069145.0. Differences from client totals are retained in`replay/evidence/decode-counter-analysis.json`; no residual is assigned a cause without request evidence. Scheduler gauges are sampled recent values, not whole-run accepted-draft averages.

## Reproduction and scope

`BASELINE-PRIMARY.json`, `preparation/`, `chart/` and the single Prefill-scale`rollout/` phase retain selected source, exact values, the replica-only diff and rollback. The7surviving pod/container identities, including both already-RS Decode workers, must match the baseline; no Decode rollout was performed. `runtime-bound.json`, `evidence/REJECTION-SAMPLING-QUALIFIED.json`, `SAMPLING-CHECKS-DRAINED.json`, `replay/GUARD-BINDING.json`, payload attestation and observer receipts preserve actual identities and checks. Original6021 HTTP-body preparation and source cache fingerprints are referenced dependencies; no request retokenization or fabricated output-length policy is implied.

All87queue gauges were idle twice and all collectors joined before closure. Source/container identities were rechecked. Raw timing export is under`../evidence/20260913_215025/`; summarized evidence, code and reproduction files are archived only after this report closes. Persistent serving remains retained. No matched flag-off speedup, maximum sustainable load beyond tested evidence, general KV-correctness guarantee or production readiness is claimed by this one arm. Priority1 and deadline duties remain governed by`../DEADLINE-GOALS-20260914.md`.

## Admission and drain distinction

All597Alexchartwindows ending at or before600s hadTTFTP50 below4s; worst3.794992037s at580s (199completedrequests). Two of132later windows reached4s; the worst was4.080042219s at682s withfivecompletions. All729validwindows, includingdrain, remaininstrictacceptance; thetwofailuresareNOTwaived. NochartwindowTPOTP99 exceeded40ms. These are20scompletioncohorts, so laterwindows canreflectTTFTincurredmuch earlier. Full load/cachebands passed. ComparedwithATT53, theadmission-periodspikeisabsentinthisarm; sourcerecipe,placement anddynamiccache/outputstochasticsdiffer, so noisolatedpatchcausalityisclaimed.
