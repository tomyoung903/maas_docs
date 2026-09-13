# CPU-only generator investigation

Serving application files, images, resources and validation thresholds are unchanged. These are isolated processes in the Alex container, with GPUs hidden and outbound connections denied. No model requests were sent.

Baseline: all11,842 saved callbacks and35,526 events replayed at their recorded real-time offsets. Event-loop heartbeat p99 **10.860145ms**, maximum31.604753ms,1,203 samples. Callback p990.072096ms, maximum20.059164ms. One snapshot per15s took up to21.739399ms. All11,842 theory results completed. Source and container hashes, stdout, exact script and exit status are preserved in `baseline/`.

The original status client performs run-list, run-detail and explicit-snapshot queries every15s; all three can request a full child snapshot. `status_triplet/` replays three snapshots with JSON response encoding per15s. This control finished all11,842 callbacks: event-loop p99 **10.570032ms**, maximum **127.238720ms**,1,203 samples. Snapshot triplet maximum46.083694ms. The isolated127ms maximum does not reproduce the full tests’ approximately51ms p99, and no timestamp attribution to snapshot work is claimed. Both subprocesses exited successfully and their tool sessions were joined.

Limitations: HTTP uploads, SSE parsing, the full CLI scheduler, live raw-event file writes and the parent HTTP process are omitted. The existing model workers are idle, so the CPU replay also does not recreate host CPU contention under live GPU serving. The baseline does not establish the cause of ATT34/35's approximately51ms event-loop p99.

A lighter observation helper, `../worker/alex_status_single.py`, uses one exact-run snapshot while active and fetches full detail after termination. Its terminal path reproduced the complete ATT35 summary exactly (`single-poll-closed-run-check/VERIFIED.json`). It does not change benchmark timing or validation formulas. Its live path will be checked in the next warmup. This reduction is not yet proven to fix the full-test delay.

The next authorized10K trial is prepared with a preserved decision amendment: ATT35 remains invalid; valid ATT33 is a reference, and final acceptance still requires the original generator, load, zero-error and strict TTFT gates. Both required CPU controls are now closed; no additional CPU variant was started.
