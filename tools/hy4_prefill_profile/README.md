# HY4 100K prefill profile

Maintained source for `docs/hy4-100k-prefill/`. This report combines a source-based
logical work ledger with an independently supplied GPU event ledger. A pending
report is valid and contains no measured values. By default, regeneration reads
the current `docs/hy4-100k-prefill/source-data.json`, preserving the measured
publication. Only a checkout without that file falls back to the pending
bootstrap snapshot. An invalid current source fails validation; it is never
silently replaced with pending data.

The main page presents one reviewed invocation: global layer index53 (the 54th
layer), PP2 local index16, chunk12 of13,8192 new tokens after90112 prior tokens.
It is a normal routed/shared-MoE layer with a full indexer refresh, selected by
structure and an existing raw-trace witness, not by its performance. It is not
an average layer. `representative-selection.json` pins its source and complete
45-event set and partitions its41 operator families into eight readable groups.
All28 reviewed leaf work/byte joins retain their existing metrics. The selected
tree additionally classifies the remaining13 families as scalar operations or
movement and supplies six independently derived useful-byte estimates.
Compute MFU is38.2158728863% for the45 captured events. Physical DRAM MBU remains
unmeasured for the original capture; a separate GPU4 replay table reports native
MQA and TopK DRAM counters with their matching NCU times. Complete request
capture coverage is not asserted.

`single_layer.py` and `semantic_tree.py` maintain the expanded model hierarchy
and selected-kernel timeline. `representative-semantics.json` is a checksum-bound
public projection of the reviewed trace/source evidence: exact safe symbols,
stream/launch geometry, useful model-work shapes, formulas and source anchors.
The layer root contains attention, the fused iHC bridge, MoE and output branches.
Its 42 terminal display operations partition the original 45 events; only the
unbound RoPE family is split into its indexer and main-attention invocations.
All 41 original family work/metric objects and all 28 reviewed work joins remain
unchanged. The tree is a semantic ownership hierarchy, not a dependency DAG.
`metric_completion.py` applies checksum-bound `representative-metric-completion.json`
after the original semantic projection. It keeps every original family work
object, raw event, count, time and full-report metric unchanged. `compute_work`
holds separate matrix-work coverage; `additional_work` holds new per-field
evidence and `scalar_work` records partial scalar coverage. An empty matrix
numerator classifies a scalar/copy operation; it does not assert zero arithmetic
or complete scalar/byte coverage. Parent compute MFU sums each precision's model
FLOPs divided by its matching nominal peak, then divides that ideal time by the
same-device interval union. It is not a calibrated TileSight latency or measured
SM activity. Interface bytes never roll up through module parents.

Rows show precision-specific useful model FLOPs, numeric interface-byte estimates,
source-derived geometry and exact captured-kernel evidence. “Locate kernels”
selects the corresponding measured timeline intervals. The full kernel symbols,
SQLite event IDs and launch geometry are available in each row's evidence details.

The main HTML embeds only selected-layer data. `full-report.html`
retains the complete rank/chunk explorer; `source-data.json`, `report-data.json`
and `input-schema.json` remain complete downloadable artifacts. The legacy
renderer (`template.html`, `app.js`, `timeline.js`, `style.css`) is maintained for
that archive. Semantic groups can interleave; their order is not a serialized
execution claim.

```bash
python3 tools/hy4_prefill_profile/build.py --validate-only
python3 -m unittest discover -s tools/hy4_prefill_profile -p 'test_*.py' -v
python3 tools/hy4_prefill_profile/build.py
```

The final command reproduces both the selected-layer main page and complete
archive from the committed source. A stale source or event-set selection fails
before replacing output. For a new measured source, supply a separately reviewed
selection with `--representative /path/to/selection.json`. To render the complete
explorer alone, call the Python `build(source, output)` function without a
representative selection. The CLI uses the committed selection by default.

For a new source ledger (private local input, public-safe output):

```bash
python3 tools/hy4_prefill_profile/import_logical_ledger.py \
  --ledger /path/to/operator-ledger.json
python3 tools/hy4_prefill_profile/build.py \
  --input tools/hy4_prefill_profile/pending-input.json \
  --output /path/to/pending-preview
```

The importer intentionally emits `status=pending`, a pending chunk placeholder,
false work/event joins, and no compute/HBM roofs. It does not infer measured
chunk boundaries from the nominal 8192-token plan. Global input/output operations
sit under explicit boundary groups, not fabricated decoder layers. All direct
source pins are retained as hashes and safe repository-relative labels; private
paths and internal URLs are not published.

For normalized measured evidence:

```bash
python3 tools/hy4_prefill_profile/build.py --input /path/to/measured-input.json \
  --representative /path/to/reviewed-selection.json
```

This command writes only the selected output pack (`--output` is optional). It
does not commit, push, update other pages, stage files or edit catalog metadata.
Shared annotations use the normal stable `/hy4-100k-prefill/` page key. A browser
review and root's publication checks remain required before publishing.

## Normalized input contract

`schema.json` describes the shape; `build.validate` is the authoritative semantic
validator. It additionally checks the baseline partition, parent/child ownership,
cycle freedom, unique event IDs, interval values, public-safe text and joins.
Every object has explicit fields; undeclared precomputed utilization is rejected.

- `schema_version`: `hy4-prefill-profile-v1`.
- `status`: `pending` or `measured`.
- `request`: exactly100000 `input_tokens`,1 `output_tokens`, baseline
  `layer_partition=[16,21,21,20]`, a safe configuration label, nullable
  `cached_tokens` and `wall_time_ms`. A measured report requires0 cached tokens,
  positive measured full-request wall time and at least one event. The explicit
  `execution_coverage_complete` assertion must have `coverage_artifact_ids`; only
  an independently verified complete request may enable aggregate request MFU.
  A partial capture can retain measured values with that assertion false. That status
  means observed timings, not automatically a fully qualified work model.
- `hardware`: ranks/devices `[0,1,2,3]`, optional named nominal
  `compute_roofs_tflops` (`nvfp4`, `fp8`, `bf16`, `fp16`, `tf32`, `fp32`, `fp64`),
  nullable `bandwidth_roof_tb_s`, and artifact IDs proving the selected roofs.
  `fp32` is scalar/SIMT throughput, never a Tensor-Core reinterpretation.
- `artifacts`: unique public-safe `id`, descriptive `label`, exact SHA256, and
  optional public HTTPS source URL. Use source/trace/counter hashes and safe
  labels; do not put private paths, services, credentials or internal links here.
- `nodes`: one model root, four rank children, actual chunk children, layer or
  explicit boundary groups, and operator leaves. All nodes have `id`,
  `parent_id`, `kind`, `label`, `rank`, `chunk`, `layer`, `work`,
  `work_matches_events` and `artifact_ids`; optional `note`, `formula`, `boundary`.
  Only an explicit boundary may have null layer below the chunk level.
  `chunk="pending"` is for the pending logical inventory; measured input should
  supply actual chunk IDs. A rank is a device-local clock domain.
- Operator `work` has `status`, nullable `flops_by_precision`, nullable
  `scalar_ops`, nullable `useful_bytes`, a `useful_bytes_note`, nullable
  `dram_bytes` and nullable `dram_counter_artifact_id`. Non-null FLOPs are exact
  nonnegative integers; `{}` means a known non-matrix operation, while null means
  unknown work. Counts are for **this operator's complete owned event set**, not
  one invocation unless exactly one invocation is owned. Scalar semantic counts
  remain separate from precision-class matrix/dot FLOPs.
- `work_matches_events=true` is admitted only after external review proves that
  the complete work/byte scope matches that operator's owned events and exact
  implementation. The boolean is a retained review assertion, not proof produced
  by this renderer. Matching artifact IDs are mandatory. A fused kernel receives
  one owner and one complete composite work numerator; do not assign its duration
  independently to several semantic components. Split logical operations only
  when time attribution independently supports the split.
- `events`: unique `id`, `rank`, nonnegative relative `start_ns`, positive
  `duration_ns`, `owner_id` (one operator or null), `artifact_id`. Preserve the
  common captured origin only when its clock provenance is established; never
  shift lanes independently for a shared-axis plot or infer cross-host
  synchronization. Without common-clock evidence, the shared timeline remains
  unavailable. Device-local interval unions are still independent. Keep all
  in-scope events, including unattributed events. Declare the capture's inclusion
  policy outside the raw record through artifact labels/limitations.
- `limitations`: clear public-facing strings documenting remaining attribution,
  timing, numerical, byte-model or operating limitations.

## Derived metrics and invariants

The builder never accepts precomputed MFU/MBU. It recomputes disjoint event
ownership, summed residency, same-device interval unions, and scalar/matrix work.
Parent FLOP components sum exact leaf integers; unknown work is never zero-filled.
Interface bytes do **not** sum through parents. Physical counter bytes stay null
without explicit counter evidence. Work/event mismatches or absent roofs leave
utilization null.

- Tree compute rate:100 × sum(F_precision/P_precision) / named time. Both
  active-union and summed-residency denominators are exposed. At a multi-device
  parent, active-union time is the sum of separate per-device unions.
- Request rate:100 × sum(F_precision/P_precision) / (4 × request wall time).
  Any unattributed event or incomplete work/join blocks this aggregate.
- Estimated MBU:100 × modeled interface bytes / (nominal HBM bandwidth × union).
  It is neither a DRAM counter nor a sum of submodule interfaces.
- Counter MBU uses matching measured DRAM bytes and remains a separate column.
  The external join review must verify that those counters use the same interval
  and owned event set; a separately timed replay cannot silently substitute.

The input should explicitly retain scheduler/communication/auxiliary work. Their
matrix/dot numerator may be `{}` while time remains measured. Unknown numerator
is null, not `{}`. A phase containing scalar operations can have a classified
matrix/dot proxy, but this does not claim all compute is Tensor-Core work.

Source estimates and nominal roof percentages are not TileSight predictions.
Neither CUPTI residency nor overlap subtraction identifies intrinsic service time
or removable waits. The report is an evidence viewer, not an optimization claim.

The full archive lazily creates expanded descendants and provides rank/chunk
filters; its parent/overview metrics retain the complete input scope. The main
page has no global explorer controls. It displays the selected invocation's
existing leaf metrics, keeps unknown group ratios null, and never sums interface
bytes through groups. Source JSON is embedded safely and downloadable.

## Reviewed nominal B300 preset

`nominal-b300-roofs.json` is an optional, source-hashed per-GPU preset for AWS
P6-B300 / HGX B300. It uses7.7TB/s HBM, rather than the GB3008TB/s specification,
and separate NVFP4/FP8/BF16/FP32 roofs. Use it only after captured hardware identity
is reviewed. It is not automatically applied to the pending input, and it does
not normalize clocks or claim achieved service rates. The model compute fraction
(MFU) compares modeled work against these nominal capacities; estimated MBU
compares modeled useful interface bytes against nominal per-device bandwidth.

## Import the private SQLite extraction

The read-only extractor emits `hy4-100k-trace-sidecar-v1`. Keep that sidecar
private; it contains raw symbols, process identities, annotation text and paths.
The public adapter copies only selected fields:

```bash
python3 tools/hy4_prefill_profile/import_trace.py \
  --sidecar /path/to/extracted-sidecar.json \
  --output /path/to/public-measured-input.json
python3 tools/hy4_prefill_profile/build.py \
  --input /path/to/public-measured-input.json
```

Actual zero-cache and positive request wall-time evidence is mandatory. If these
are absent from the sidecar, `--request-receipt` accepts a JSON object with
`sidecar_sha256`, `input_tokens`, `output_tokens`, `cached_tokens`, `wall_time_ms`
and `layer_partition`. Any contradiction with non-null sidecar values fails.
The receipt file itself is hashed into public provenance.

Each resolved `(rank, forward, layer-or-boundary, family)` forms one operator
owner. Raw names are not copied. Unresolved correlations stay `owner_id=null`.
`kernel`, `memcpy` and `memset` remain distinct activity kinds; counts say GPU
events rather than calling copies kernels. A rank with no known owner receives
an explicitly empty attribution placeholder, while its unknown event time stays
in the full-GPU summaries. Source-order family/layer labels are inference until
independently checked; the adapter makes no arithmetic join from those labels.

Observed log chunk rows alone are insufficient: an individual forward also needs
matching non-null token/context fields and the declared FIFO context method.
This prevents accidentally matching the first thirteen forwards by ordinal when
forward counts differ from the profile-bracket log. Zero-duration omitted-event
counts are surfaced as a limitation when present in extraction coverage.

Optional, separately reviewed bindings:

- `--work-bindings`: JSON schema `hy4-reviewed-work-bindings-v1` with
  `sidecar_sha256`, public-safe `artifacts`, and `bindings`. Each binding has
  `node_id`, `event_ids_sha256`, `reviewed_complete_operator_scope=true`, a full
  `work` object, and `artifact_ids`. The event-set hash is SHA256 of the sorted
  complete string-ID list encoded as compact JSON (Python separators `(',',':')`).
  It must cover the whole fused operator's owned event set; partial suboperation
  FLOPs may not be divided by a complete fused interval. Non-matching event hashes
  fail. This admission is an external review assertion, not a renderer proof.
- `--coverage-review`: schema `hy4-request-coverage-review-v1`, exact
  `sidecar_sha256`, `complete=true`, `all_four_ranks_all_request_events=true`.
  Any still-unattributed event rejects complete coverage. Missing work bindings
  continue to prevent aggregate MFU even with complete event coverage.
- `--nominal-roofs tools/hy4_prefill_profile/nominal-b300-roofs.json` requires
  `--hardware-receipt`: exact `sidecar_sha256`, `rank_ids=[0,1,2,3]`, captured
  `device_name` identifying B300 rather than GB300, and
  `nominal_preset_reviewed=true`. This file is hashed into provenance. The preset
  is never silently applied to arbitrary measured input.

Those options do not authorize any GPU run or publication. The adapter makes no
network calls. Default work, numerical qualification, and DRAM-counter values
remain unavailable until their explicit evidence is supplied.

## Measured timeline

`timeline.js` adds a four-rank canvas panel with a common time axis, chronological
forward spans, compute/communication/memory/unknown colors, exact hover data,
zoom, a position slider, and drag/Shift-wheel panning. Small intervals have a
one-pixel minimum drawing width; exact durations and overlaps remain in data.
There is no generated example waveform in the pending document.

A new optional input `timeline` object contains `clock_alignment`, nullable
`origin_ns`, nullable source `artifact_id`, a `clock_evidence` description and
`chunks`. Only `clock_alignment="single_host_nsight_common_origin"`, matching
measured evidence and a retained origin enable a common axis. Otherwise the
panel states that shared alignment is unavailable. The adapter preserves all
`start_ns` values verbatim, never resetting each rank to its own first event.
The origin is retained exactly, with a string copy in derived metadata.

A chunk span records `node_id`, `rank`, `forward_ordinal`, `start_ns`,
`duration_ns` and nullable `new_tokens`. It is the observed correlated forward
window, not the sum of its event durations. The corresponding forward/tree node
must exist. No chunk interval is created from nominal token counts alone.
Events optionally carry `category` (`compute`, `communication`, `memory`,
`unclassified`); the adapter uses stable family names for communication and
explicit activity kind for copies/memsets. “Compute” includes other noncommunication
GPU kernels and does not imply Tensor-Core instructions.

Pure timeline math tests (no browser or fabricated published data):

```bash
node tools/hy4_prefill_profile/test_timeline.js
```

The model compute fraction labels explicitly mean matrix/dot MFU. Semantic
scalar counts are visible separately and do not receive a fabricated tensor
peak. Actual browser rendering remains a separate check from syntax/math tests.

### Whole-request useful target-model MFU

`--target-model-work` accepts a `hy4-target-model-work-v1` receipt bound to the
sidecar SHA, with public artifacts and a `work` object containing
`flops_by_precision`, `scope`, `source_artifact_ids`, `request_artifact_ids`,
`request_completed`, `input_tokens`, and `output_tokens`. The source numerator
is independent of trace ownership. The optional derived
`target_model_request_mfu_percent` is `100*sum(Fp/Pp)/(4*client_wall_seconds)`.
It includes only the explicitly stated useful target-model work while auxiliary,
draft and idle overhead remain in the wall denominator. This does not loosen the
existing `request_mfu_percent` event-completeness conditions. No physical whole-
request MBU is inferred.

Request fields `profiled_server_prefill_ms` and `warmup_server_prefill_ms` are
optional, provenance-bound observations. The profiled client wall time remains
`wall_time_ms`. The separate preparation call is never presented as a comparison
baseline or a speedup.

The exact current measured publication can be regenerated from its committed
normalized source without access to private traces:

```bash
python3 tools/hy4_prefill_profile/build.py \
  --input docs/hy4-100k-prefill/source-data.json \
  --output docs/hy4-100k-prefill
```

The no-argument command selects that same current source when it exists. For a
new capture, pass the newly reviewed normalized input explicitly. A pending
preview requires an explicit pending input whenever a current source exists.

### Audited NCCL identity without forward ownership

A separate identity audit can color known NCCL intervals as communication while
leaving `owner_id=null`. `enrich_nccl.py` verifies the audit manifest, sidecar and
SQLite hashes, shared origin, and each event ID/rank/interval before adding only
`category=communication`, `communication_direction`, and a classification
artifact reference. It adds public-safe audit hashes and a scope limitation;
private audit payloads are not copied. It never infers a peer, byte count,
forward, work numerator, or recoverable time. The enriched normalized source is
preserved by the normal default rebuild.

```bash
python3 tools/hy4_prefill_profile/enrich_nccl.py \
  --input docs/hy4-100k-prefill/source-data.json \
  --audit /path/to/reviewed-nccl/result.json \
  --manifest /path/to/reviewed-nccl/manifest.json \
  --output /path/to/enriched-source.json
python3 tools/hy4_prefill_profile/build.py --input /path/to/enriched-source.json
```

## Separate physical-counter replay

`physical_replay.py` validates `isolated-replay-counters.json`, whose checksum is
pinned in the representative selection. It derives physical bandwidth and MBU
only from each replay kernel's measured bytes and matching NCU duration, using
the page's existing7.7 TB/s nominal roof. Exact native symbols and the original
selected event set bind the comparison; no replay value modifies an original
event, tree time, MFU or useful-byte MBU. The public summary retains raw integer
bytes/durations, numerical scope, replay conditions and artifact hashes, without
private inputs, tensors, host paths or credentials.

The rendered `isolated-replay-counters.json` download includes derived totals and
percentages. One baseline chain precedes the selected counter chain; each chain
launches MQA then TopK without an intermediate host copy or synchronization.
Initial cache state is uncontrolled, clock/cache controls are disabled, and each
profiled native kernel has exactly one pass. Counter-run durations are never
substituted for original trace durations.

The adjacent routed-MoE block uses the separately checksum-bound
`isolated-moe-range-counters.json`. It reports one complete PDL-preserving
app-range, not individual kernels: 7,515,448,832 DRAM bytes and 795,469,606
requested L2 sectors. Its 5.20944 ms denominator is the explicit NCU range
wall clock, including unquantified host/profiler overhead and a deprecation
warning at the measured callsite. The derived 1.44266 TB/s is complete
profiled-range bandwidth; no native-kernel MBU, per-FC attribution, cache-hit
ratio, unprofiled latency or speedup is derived. Two full 50,331,648-value
outputs match the captured baseline exactly. The public download retains
integer counters, separate capture identity and raw artifact hashes.

## Serialized FC1/FC2 physical counters

`serialized-moe-fc-counters.json` is a separately checksum-bound real-a2 baseline observation. It uses application replay and matched per-kernel `gpu__time_duration.sum`, distinct from the earlier aggregate app-range wallclock. `physical_replay.derive_moe_fc` recomputes exact totals, decimal TB/s and physical MBU against the declared7.7TB/s roof. The new table never updates original events/tree metrics or either prior counter dataset. It retains raw CSV/report and independent actual audit hashes without private paths. Serial profiling changes native PDL overlap/cache evolution; concurrent native MBU, X and gain remain unknown.
