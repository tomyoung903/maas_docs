# Normalized Batch-Sweep Report Data

`build_html_report.py` consumes one JSON object and produces a self-contained
MaaS Docs report. The generator is intentionally tolerant of partial captures:
unknown values render as `Not captured`, while structural errors still fail
fast.

## Command

```bash
python3 build_html_report.py \
  --input normalized_report.json \
  --output-dir report_maas
```

The only required top-level keys are `schema_version`, `experiment`, and
`batches`. `batches` must contain exactly the string keys `"1"`, `"10"`, and
`"100"`.

## Shape

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-03T15:00:00+08:00",
  "experiment": {
    "title": "GLM-5.2 FP8 TP=8 Decode Batch Sweep",
    "subtitle": "One computed decode step at batch sizes 1, 10, and 100.",
    "cluster": "Japan",
    "node": "gpu-h200-36",
    "gpu": "NVIDIA H200",
    "model": "zai-org/GLM-5.2-FP8",
    "model_revision": "ba978f7d347eaf65d22f1a86833408afdb953541",
    "runtime_image": "registry/image:tag",
    "context_tokens": 4096,
    "max_new_tokens": 2,
    "precision": "FP8",
    "topology": {"tp": 8, "dp": 1, "ep": 1, "pp": 1},
    "cuda_graph_batches": [1, 10, 100],
    "hardware": {
      "peak_tflops": null,
      "hbm_tb_s": null,
      "sources": []
    },
    "contract": ["All requests enter one native batched generate call."],
    "limitations": ["MFU and MBU are modeled unless counters are supplied."]
  },
  "validation": {
    "status": "pass",
    "checks": [
      {"name": "Batch membership", "status": "pass", "evidence": "..."}
    ]
  },
  "batches": {
    "1": {"status": "complete"},
    "10": {"status": "complete"},
    "100": {"status": "complete"}
  },
  "comparison": {
    "headline": "Optional authored comparison conclusion.",
    "observations": []
  },
  "artifact_manifest": "artifact_manifest.json",
  "downloads": []
}
```

## Per-batch object

Every field below is optional except `status`. Numeric durations are
milliseconds unless a key explicitly names another unit.

```json
{
  "status": "complete",
  "errors": [],
  "warnings": [],
  "proof": {
    "requested_batch": 10,
    "observed_real_batch": 10,
    "cuda_graph_batch": 10,
    "prefill_rows": 0,
    "decode_rows": 1,
    "speculative": false,
    "request_ids": ["rid-0", "rid-1"]
  },
  "timing": {
    "samples_ms": [21.1, 20.8],
    "sample_count": 30,
    "p25_ms": 20.7,
    "median_ms": 20.9,
    "p75_ms": 21.2,
    "p95_ms": 21.8,
    "min_ms": 20.4,
    "max_ms": 22.0,
    "throughput_tokens_s": 478.5,
    "latency_inflation_vs_b1": 2.7,
    "effective_parallel_gain": 3.7
  },
  "kernel_timing": {
    "boundary": "gpu0_active_kernel_interval_union",
    "active_union_ms": 22.756136,
    "kernel_active_tokens_s": 439.441916,
    "batch_scale_vs_b1": 10,
    "active_time_inflation_vs_b1": 1.25208,
    "kernel_rate_gain_vs_b1": 7.986707,
    "ratio_identity_product": 10.0,
    "graph_wall_span_ms": 23.911701,
    "idle_gap_ms": 1.155565,
    "summed_residency_ms": 24.472106,
    "overlap_excess_ms": 1.71597,
    "http_request_latency_included": false
  },
  "graph": {
    "wall_span_ms": 20.1,
    "aggregate_kernel_ms": 148.2,
    "launches": 3280,
    "distinct_kernel_names": 92,
    "start_offset_ms": 1.3,
    "cleanup_wall_span_ms": 3.2,
    "cleanup_aggregate_kernel_ms": 20.0,
    "cleanup_graph_execution_count": 8
  },
  "rendezvous": {
    "arrival_spread_ms": 0.22,
    "latest_rank": 3,
    "first_collective_ms": 1.47,
    "notes": []
  },
  "efficiency": {
    "modeled_flops_t": 34.2,
    "mfu_pct": 22.1,
    "modeled_min_bytes_gb": 181.0,
    "mbu_min_pct": 31.4,
    "measured_dram_bytes_gb": null,
    "measured_hbm_bw_tb_s": null,
    "active_union_ms_by_rank": {
      "0": 18.4,
      "1": 18.2
    },
    "metric_label": "Modeled",
    "notes": []
  },
  "categories": [
    {
      "id": "attention_indexer",
      "label": "Attention indexer",
      "color": "#0f766e",
      "launches": 78,
      "residency_ms": 2.1,
      "share_pct": 14.2,
      "cleanup_residency_ms": 0.0
    }
  ],
  "rank_spans": [
    {
      "rank": 0,
      "start_ms": 1.20,
      "end_ms": 21.30,
      "first_collective_ms": 1.46,
      "push_ms": 0.26
    }
  ],
  "chronology": [
    {
      "id": "mla",
      "label": "MLA attention",
      "category": "attention_mla",
      "start_ms": 2.1,
      "end_ms": 3.8,
      "color": "#2563eb",
      "note": "Optional tooltip text"
    }
  ],
  "density_bins": [
    {
      "start_ms": 0.0,
      "end_ms": 0.1,
      "capacity_gpu_ms": 0.8,
      "categories": {"attention_mla": 0.22, "moe_up_gemm": 0.31}
    }
  ],
  "kernel_tree": {
    "id": "root",
    "label": "One computed decode step",
    "category": "root",
    "launches": 3280,
    "time_ms": 148.2,
    "share_pct": 100.0,
    "modeled_flops_t": 34.2,
    "mfu_pct": 22.1,
    "modeled_min_bytes_gb": 181.0,
    "mbu_min_pct": 31.4,
    "metric_label": "Modeled",
    "note": "Optional interpretation",
    "children": []
  },
  "one_rank_tree": {
    "scope": {
      "device": 0,
      "rank_label": "DP0 / TP0 / EP0",
      "launch_count": 3575,
      "graph_wall_span_ms": 23.911701,
      "active_union_ms": 22.756136,
      "idle_gap_ms": 1.155565,
      "aggregate_kernel_ms": 24.472106,
      "overlap_excess_ms": 1.71597
    },
    "constants": {
      "fp8_peak_tflops": 1979.0,
      "bf16_peak_tflops": 989.5,
      "hbm_tb_per_second": 4.8
    },
    "tree": {},
    "layer_ledger": [],
    "method": {}
  },
  "top_kernels": [
    {
      "name": "kernel symbol",
      "category": "moe_up_gemm",
      "launches": 75,
      "residency_ms": 4.4,
      "share_pct": 11.2,
      "mean_us": 58.7
    }
  ],
  "events": [
    {
      "rank": 0,
      "start_ms": 1.2,
      "duration_us": 58.7,
      "category": "moe_up_gemm",
      "kernel_name": "kernel symbol",
      "graph_node": 123
    }
  ],
  "artifacts": [
    {"label": "Nsight capture", "path": "captures/b10.nsys-rep"}
  ],
  "notes": []
}
```

## Download declarations

`downloads` can contain a relative path string or an object with `path` and an
optional `label`. Existing files are copied under `report_maas/downloads/`.
Missing declared files are rejected, because publishing a broken evidence link
would make the report misleading.

The input `timing` object is the unprofiled client HTTP envelope. For this
batch-sweep report, the generator removes it from the published normalized
batch objects after validating the input and derives `kernel_timing` from the
exact GPU-0 kernel intervals. The raw timing-sample CSV remains downloadable as
excluded evidence, but it is not used by any displayed time, rate, or ratio.

The generator always writes these normalized artifacts:

- `report_data.json` — the validated, normalized sidecar used by the page.
- `timeline_data.json` — an alias retained for the baseline report format.
- `gpu0_kernel_tree.json` — all three exact GPU-0 operation trees, modeled
  numerators, raw-name leaves, and 78-layer ledgers.
- `experiment_summary.json` — compact cross-batch timing and efficiency data.
- `validation.json` — validation ledger.
- `batch_summary.csv` — one row per batch.
- `kernel_summary.csv` — one row per batch and kernel family.

For this capture-specific generator, `one_rank_tree` is derived from the full
adjacent `kernel_events.csv.gz` rather than trusted from the input JSON. The
classifier uses GPU 0 graph-node order, validates all 78 layer motifs, and
requires every useful node to reconcile exactly once. Each node carries both
the interval union used for MFU/MBU and the overlap-additive summed residency
retained as a diagnostic; child interval unions are intentionally non-additive.

## Artifact manifest

Artifact evidence is optional. When `artifact_manifest.json` is adjacent to the
input sidecar, the generator discovers it automatically. It can instead be
declared with a relative path:

```json
{"artifact_manifest": "evidence/artifact_manifest.json"}
```

or embedded as a JSON object under `artifact_manifest`. A path declaration must
remain below the input sidecar's directory. The manifest itself is copied to
`downloads/artifact_manifest.json`.

The normalizer accepts artifact arrays or maps under `artifacts`, `files`, or
`remote_artifacts`, as well as direct `sqlite`, `nsys_rep`, and `server_log`
entries. It recognizes the following optional fields without inventing missing
values:

```json
{
  "artifacts": {
    "capture.sqlite": {
      "path": "remote/capture.sqlite",
      "size_bytes": 123456,
      "sha256": "hex digest",
      "quick_check": "ok"
    },
    "capture.nsys-rep": {
      "path": "remote/capture.nsys-rep",
      "size_bytes": 234567,
      "sha256": "hex digest",
      "integrity": "stable across two checks"
    },
    "server.log": {
      "path": "remote/server.log",
      "size_bytes": 345678,
      "sha256": "hex digest",
      "status": "complete"
    }
  }
}
```

The remote-analysis manifest shape is also accepted directly. Its
`sqlite_validation` object is folded into the SQLite artifact's integrity cell;
it does not create a synthetic fourth artifact:

```json
{
  "sqlite_validation": {
    "open_mode": "read-only immutable",
    "pragma_quick_check": ["ok"],
    "kernel_table": "CUPTI_ACTIVITY_KIND_KERNEL",
    "kernel_rows": 987654,
    "status": "pass"
  },
  "artifacts": [
    {
      "role": "nsight_sqlite",
      "path": "/profiles/run.sqlite",
      "size_bytes": 1001,
      "sha256": "hex digest"
    },
    {
      "role": "nsight_report",
      "path": "/profiles/run.nsys-rep",
      "size_bytes": 1002,
      "sha256": "hex digest"
    },
    {
      "role": "server_log",
      "path": "/profiles/server.log",
      "size_bytes": 1003,
      "sha256": "hex digest"
    }
  ]
}
```

Only the manifest is copied automatically; the large capture artifacts remain
at their recorded locations unless they are separately declared in
`downloads`.

## Metric provenance

Only populate `mfu_pct`, `mbu_min_pct`, `modeled_flops_t`, or
`modeled_min_bytes_gb` when the analysis produced them. The report labels these
values with `metric_label` and never silently derives H200 peaks. If
`experiment.hardware.peak_tflops` or `hbm_tb_s` is supplied, add a directly
supporting source in `experiment.hardware.sources`; the generator rejects an
unsourced non-null peak. A source can be a string or an object with `label` and
`url`.
