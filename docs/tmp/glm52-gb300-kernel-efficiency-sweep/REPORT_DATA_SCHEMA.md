# Kernel efficiency sweep input contract

`build_report.py` accepts exactly schema version 1. Unknown keys, missing keys,
wrong types, non-finite values, unordered/missing batch points, dangling artifact
references, malformed percentile intervals, unknown compute roofs, duplicate IDs,
and impossible derived utilization above 110% are hard errors.

The required top-level keys are:

- `schema_version`: integer `1`.
- `synthetic`: boolean. Real publishable evidence must use `false`.
- `report`: title, explanatory subtitle, UTC generation timestamp, experiment ID,
  and the B = 100 time-agreement tolerance.
- `provenance`: hardware, immutable software identity, TP/DP/EP/PP topology, and
  measurement protocol.
- `roofs`: one or more named compute roofs in TFLOP/s plus one peak HBM roof in
  TB/s. Every roof must name its source.
- `batch_sizes`: exactly `[1, 10, 20, 100, 200, 500]`.
- `artifacts`: stable IDs, artifact kinds, paths, SHA-256 digests, and descriptions.
  The publish pack uses safe relative download paths; recognized kinds include
  normalized JSON, CSV, profiler evidence, source snapshots, and manifests.
- `coverage`: catalog/included counts, excluded-family reasons, and counts of
  available versus unavailable full-trace comparisons.
- `families`: at least one kernel-family record.
- `limitations`: at least one explicit limitation.

Each family requires:

- a stable `id`, title, semantic category, operation description, and comparison
  basis;
- a `compute_roof_key` that resolves into `roofs.compute`;
- prose definitions of its FLOP and useful-byte floors;
- six ordered `points`, one for each declared batch;
- a normalized `full_b100` observation using the same comparison basis;
- an interpretation note.

Each standalone point supplies primary `time_us`, a `time_basis` of
`kernel_active_union` or `eager_operator_interval`, the secondary
`operator_interval_us`, nullable `kernel_summed_residency_us`, `samples`,
nullable `non_kernel_interval_us`, `p10_us`, `p90_us`, nullable
`modeled_flop`, nullable `useful_bytes`, and an evidence record. Kernel-union
evidence requires summed residency and the per-sample non-kernel median, and
cannot exceed residency. Eager-only evidence must use the operator interval as
primary and must leave both correlated fields null. Evidence is `exact`, `proxy`, or
`unavailable`, and separately preserves the source status (`ok`,
`trace-matched`, or `unavailable`). Raw symbols may be empty for CUDA-event-only
standalone evidence; a claimed trace match must carry at least one exact raw
symbol. Adapter-produced correlated evidence also supplies `raw_kernel_stats`
with per-symbol launch counts and summed residency across the associated sample
set. When present, its names must match `raw_kernel_names` exactly.

The full B = 100 record declares `availability` as `matched` or `unavailable`.
A matched record requires positive time and invocation count plus
`trace-matched` evidence. An unavailable record requires null time and count.
Modeled FLOP and useful bytes remain nullable independently. The current GB300
adapter emits a matched record only when the event-level mapping proves semantic
ownership and its join audit proves identical raw-symbol signatures, common
image/source provenance, compatible launch configuration, and a transferable
work model. Nsight Systems did not export cubin hashes for this experiment, so
the mapping records that absence explicitly and does not claim direct cubin
identity. A semantic
owner that fails that stricter audit remains unavailable; its selected-replay
time is not silently compared with a different standalone implementation. The
routed MoE full-replay byte floor deliberately stays null even after an exact
join because production expert IDs were not captured. If both standalone and
selected-replay work models are present, they must agree exactly under the
declared comparison basis.

MFU and MBU-min are not accepted from input. The builder derives each only when
elapsed time, the matching work floor, and the corresponding roof are all
available; otherwise it renders an explicit unavailable value. It also derives
the standalone-versus-full B = 100 delta and agreement badge only for a matched
trace owner. This makes displayed arithmetic reproducible without turning
missing evidence into zero.

`adapt_real_evidence.py` is the evidence-producing adapter. It consumes the
standalone sweep JSON, finalized GPU 0 tree, B = 100 trace summary, optional
event-level family mapping, optional normalized Nsys range summary, and the
required correction-overlay manifest when a merged sweep declares overlays; hashes
every supplied input; checks hardware, topology, context, source revision,
sample counts, medians, interval arithmetic, symbol totals, and family coverage;
and then calls this schema validator. When `--mapping` is supplied, its
`kernel_family_index` must exactly equal the tree's non-owning family index, its
event sets must be disjoint and reconcile with the selected replay, and its
family-rule audit must pass. The mapping is authoritative for event-level
semantic ownership; the global raw-symbol summary is used only for the subset it
can reconcile without splitting a shared symbol among semantic owners. A
selected-replay comparison is admitted only when the indexed node has role
`kernel_family`, explicit logical invocations, `active_union_ms` as its basis,
and `work_model_join.inheritance_eligible` is true. The trace summary must either
pass outright or match the single reviewed two-replay attribution exception
while every mechanical membership check passes.

## Normalized Nsys range contract

`adapt_real_evidence.py --nsys-summary` accepts exactly schema
`glm52-gb300-kernel-sweep-nsys-ranges-v1`. The top level contains
`schema_version`, `status` (`pass`), `source_sweep_sha256`,
`source_sqlite_sha256`, `device_id`, `measurement_semantics`, and `rows`.
Measurement semantics must define `kernel_active_union_us`,
`kernel_summed_residency_us`, `non_kernel_interval_us`, and
`source_cuda_event_us`.

There must be one row for every successful eager family/batch pair and no other
rows. Each row identifies `family_id`, `batch`, `mode` (`eager`), `phase`
(`sample`), ordered per-sample records, and aggregate `raw_symbols`. A sample
contains `index`, `source_cuda_event_us`, `nvtx_cpu_range_us`,
`kernel_launches`, `kernel_active_union_us`,
`kernel_summed_residency_us`, `kernel_envelope_us`, and
`non_kernel_interval_us`. Raw symbols contain exact `kernel_name`, `launches`,
`summed_residency_us`, and counted launch configurations (grid, block,
registers per thread, and static/dynamic shared bytes). Source samples must equal the sweep JSON; union,
residency, envelope, and non-kernel arithmetic must reconcile; and symbol totals
must equal all per-sample launch and residency totals.

## Event-level selected-replay mapping contract

`adapt_real_evidence.py --mapping` accepts schema
`glm52-gb300-kernel-family-mapping-v1`. It carries generation identity and
scope, active-union comparison semantics, mapped and unmapped event counts, raw
symbol rules, a non-owning `kernel_family_index`, per-family rule audits,
mechanical validation, and a safe-subset reconciliation against the global
rank-0 raw-symbol summary. The mapping index must be byte-for-byte equivalent as
JSON data to `gpu0_kernel_tree.json.kernel_family_index`; this prevents a report
adapter from silently using ownership data from a different extraction run.

Every indexed family declares its complete event IDs, active union, summed
residency, exact raw symbols, logical invocation count, and `work_model_join`.
The adapter rejects overlapping event sets, count or timing contradictions,
unknown sweep families, failed audits, or a failed safe-summary reconciliation.
`inheritance_eligible` is the final gate for a displayed B = 100 comparison; a
semantic mapping by itself is not enough. The mapping also carries a strict
B = 100 normalized-signature audit and an eight-rank symmetry audit. Every TP
rank must independently reproduce the same family mapping fingerprint and
event multiplicities before the adapter accepts the evidence.

## Correction-overlay contract

A sweep whose provenance declares `correction_overlays` must be accompanied by
`--overlay-manifest`; a primary unmerged sweep must not supply one. The manifest
uses schema `glm52-gb300-kernel-sweep-correction-overlay-v1` and binds the
merged sweep and Nsys hashes, all primary/correction source hashes, the exact
eight-family and six-batch replacement set, and the later 12-row BMM precedence
override. The adapter also requires the merged sweep's embedded overlay records
to agree with the manifest. This prevents a corrected B = 100 signature from
being combined with uncorrected timing rows.

The only synthetic example is `tests/fixture.synthetic.json`. The normal CLI
rejects it. `--allow-synthetic` exists solely to render a disposable test preview.
