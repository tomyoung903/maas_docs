# Code and configuration ledger

These are experiment changes. No claim is made that they were merged into the main SGLang branch or deployed to production. The shared SGLang working tree has unrelated user edits; they are not part of the experiment snapshots.

## Retained serving code

Frozen SGLang: `/mnt/HPC/tom/experiments/glm53-optim-exp-1p1d/sources/sglang-6d08e28b0c0691899973e3f11bf01fdbdf192a63`.

The six original optimizations modify `scheduler_pp_mixin.py` and `prefill.py`: earlier control-bundle publication; forward launch before prior-output handling; earlier prior-output publication; early transfer of already cached prefix KV; final page-map reuse; same-iteration nonfinal page-map copy overlap. Their cumulative patch is preserved at `/mnt/HPC/tom/pd-queue-overnight-20260912.twotxxas/candidates/same-iteration-map-copy/cumulative-against-frozen.patch`, with reconstruction and lifetime/ordering checks next to it.

The later producer CUDA-event fix waits for KV-producing GPU work before transfer. It is retained in `candidates/optimized-async-kv-event/event-on-six-patches.patch`. That patch is incremental on the six optimizations, not a complete patch against frozen source. The complete files actually mounted into the workers are in each arm's `chart/files/`; corresponding `chart/templates/` and the rendered DGD specify mounting and startup order.

Current Prefill hashes through ATT35:

| File | SHA256 |
|---|---|
| `srt/managers/scheduler_pp_mixin.py` | `b3b95b176a6185a34b75664cda8aecc921989b9e50fa5efea268d3e207c07d41` |
| `srt/disaggregation/prefill.py` | `03a7e10add300de5bb51cefe767e49dd84187b375c998c7a16341230ea603ac3` |
| `srt/disaggregation/mooncake/conn.py` | `f34c28b27d812835d7b36d8074c12853aeb169a7c3261046c773262d304581ff` |

Actual per-role source verification and image/container IDs are recorded in `evidence/runtime-attestation.json`, `runtime-bound.json`, and final `replay/evidence/DRAINED.json`. A filename or image tag alone is not source verification.

## Combined reproducible source patch

`candidates/optimized-async-kv-event/complete-against-frozen.patch` combines the six optimizations and producer-event wait against frozen SGLang commit `6d08e28b0c0691899973e3f11bf01fdbdf192a63`. It applied cleanly to fresh copies of the three original files, and all reconstructed SHA256 hashes exactly match the runtime verified in ATT33. Patch SHA256: `44a9e0aa6f2e9d897c1aad7e2310d057c5cddcf5ad9a89278903343589713c9c`. Verification: `complete-patch-verification.json` beside the patch. Other pre-existing runtime overlays remain dependencies.

This combined export was finalized after the ATT33 milestone archive; that archive already includes the complete mounted chart files. It is preserved as an additional source artifact, not a retrospective runtime change.

## Recent configuration changes, with no new serving-code patch

| Arm | Change | Exact recipe |
|---|---|---|
| ATT31 | Candidate05 workload and 8K Prefill graphs | `attempt31-two-prefill-matched-rate/preparation/` |
| ATT32 | Frontend session-affinity TTL 1800s | `attempt32-two-prefill-session-affinity/preparation/` |
| ATT33 | Frontend projected-load escape threshold 8000ms → 0; affinity retained | `attempt33-two-prefill-strict-affinity/preparation/` |
| ATT34 | Both Prefill chunk/max-prefill limits 8192 → 12288 and matching graph size; all frontend/Decode/Store settings retained | `attempt34-two-prefill-12k-strict-affinity/preparation/` |

ATT35 is an unchanged repeat of ATT34 after its generator failed the existing50ms event-loop-lag gate. No runtime/source/image/resource/validation changes are made; it retains all eight pod/container incarnations and uses a fresh cache reset. Its copied recipe, fresh attestations and reused bounded-check provenance are explicit in `attempt35-two-prefill-12k-repeat/preparation/PREPARED.json`. It is a new experiment record, not a new serving-code change.

Each rollout directory contains before/trial values, complete before/after renders, a machine-checked scope diff, command, rollback command and SHA256 hashes. ATT34 changes only two Prefill pods; six other pod/container incarnations must remain unchanged. This control asks whether Prefill throughput headroom reduces TTFT queues with locality already improved.

## Native frontend provenance

Active native extension SHA256: `940d698e115b88236ed1266f3f8b78daf0471c1159a26ccf0fe83a4264f87d3f`. Installed wheel SHA256: `6b6bd53e3ce2fe0d7b67dca4e4f02690a3d5439bb6d4886bc20b23355a006a6b`. Retained wheel and launcher: `/mnt/HPC/tom/experiments/glm53-optim-exp-1p1d/native-patches/minijinja222-dc392/`.

The wheel's referenced Dynamo commit is `dc39202c7d67a76f40efab53d1cfc3485489d838`, parent `ff778ed59d00979737e278d228ddbfe32b82c296`. Read-only GitLab metadata shows this change affects dependency locks and a GLM reasoning test, not the affinity selector/coordinator. A complete build receipt excluding uncommitted source changes is still unavailable. Keep that limitation; the exact installed binary and wheel are preserved.

## Reproduction discipline

Use the arm's complete chart and values, not only the incremental patch. Recheck live ownership, exact namespace/release, no active replay, idle queues and resource scope before applying. Verify source/image identities and all intended ranks after rollout. Run bounded retrieval/L3/routing checks, then the recorded fresh-cache warmup and exact measured schedule. Preserve every outcome, including failed setup checks, unknown counters and interrupted replays. Do not replay stale pod IDs blindly.

Historical preparation state, superseded by the amendment below: ATT36 was prepared only: Prefill chunk/max-prefill12288→10240 and graph-size12288→10240. All serving source/images remain unchanged. The rendered scope check found only these three Prefill arguments changed. Apply is gated on completed valid ATT35, full accounting, collector closure, idle queues and fresh ownership/identity checks. Initial Prefill bindings will change with worker IDs; frontend/Decode session retention is recorded separately. Recipe: `attempt36-two-prefill-10k-strict-affinity/preparation/`.

## Generator investigation after ATT35

ATT35 closed with all requests successful but a second invalid generator result (event-loop lag p99 51.507188ms >50ms). At that checkpoint ATT36 was prepared and held; the later amendment/apply below supersedes that state. No serving or generator application source, resource, image or validation limit has changed. `worker/cpu_generator_callbacks.py` replays saved callbacks in a separate CPU-only process; `worker/run_cpu_generator_callbacks.py` records its exact source hash, bound container, stdout and exit status in `generator-cpu-audit/`. Hypotheses and controls are separate from proven findings.

ATT35 retained all session-to-worker placements from ATT34 despite fresh KV reset. This state factor and inherited bounded-check provenance are part of its reproduction record.

ATT36 decision amendment: the original valid-ATT35 prerequisite is preserved in `preparation/PREPARED.json` and `apply-original-valid-baseline-gate.py`. `preparation/DECISION-AMENDMENT.json` allows the next investigation after both CPU controls close, using valid ATT33 as a reference and ATT34/35 only as diagnostics. Every original acceptance threshold remains. The prepared observer reduces our active status query from three snapshots to one every15s; it does not modify the generator application. No isolated chunk-size causal estimate is claimed. `worker/alex_status_single.py` recovered ATT35’s entire final summary exactly; its live path will be checked at warmup.

At 2026-09-13T17:45:58.184127+08:00 ATT36 applied only the three prepared Prefill arguments for10K chunk/max-prefill/graph size. Watcher session34037 is checking both Prefill replacements while preserving the other six incarnations. No benchmark has started. Prior held/prepared states above remain historical.

ATT36 also records OS scheduling/cgroup counters for the exact measured Alex child with `worker/sample_generator_process.py` (10Hz process counters,1Hz CPU cgroup counters). This is an external read-only observer, not a Python hook. Kernel schedstats availability is recorded, so unavailable zero counters cannot be presented as absence of contention. The sampler must finish and be joined before the milestone closes.

ATT36 finalized 2026-09-13T18:18:24.558013+08:00: serving remains10K andidle afternegativeguardstop. No additional serving-source patch; the combined seven-change patch is unchanged. `REPORT.md`, exactrenders/bindings, rawtimings, stopreceipt, partialload/storeaudits, placementcounts andOSsamplingclosure are preserved. New analysis/recordkeeping utilities: `worker/audit_partial_load_cache.py`, `compare_10k_stages.py`, `record_tool_session.py`; expandedmilestonesnapshot includes observer/guard receipts. These utilities do not mutate serving code.
