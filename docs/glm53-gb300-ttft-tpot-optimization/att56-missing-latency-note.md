# Median sensitivity to missing generation

ATT56 has23protocol successes with no visible generation or TTFT. For every one of603Alex20second completion cohorts, rank all unknown latencies after all observed values. The largest resulting median upper bound is3.9002034459263086seconds at507seconds, compared with the observed-only median3.897844326682389seconds. That cohort has401protocol successes,399observed timings and2unknowns. The maximum missing count in any cohort is3. All603upper bounds remain below4seconds. Overall P50/P99upper bounds are2.8407292638439685/5.022756406986154seconds.

This is a worst-rank sensitivity analysis over the actual completion cohorts, not a replacement for missing timestamps. No timing file, benchmark result or acceptance gate was changed. A request with no generation still fails coverage. The result shows that excluding the23timings does not explain the median target achievement.

The same analysis for generator-invalidATT55 also leaves all603median upper bounds below4seconds (worst3.973114273045212). That does not repair ATT55 generator validity.

Exact method and every cohort are retained in LATENCY-SENSITIVITY-BOUNDS.json; worker/bound_missing_generation_medians.py uses the original archived timing events and Alex cohort boundaries with source hashes.
