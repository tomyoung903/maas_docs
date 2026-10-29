#!/usr/bin/env python3
"""Extract the correlation-owned two-kernel active union from Nsight SQLite."""
from __future__ import annotations

import argparse
import bisect
import csv
import json
from pathlib import Path
import re
import sqlite3
import statistics


def quantile(values, p):
    s = sorted(values)
    pos = (len(s) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def interval_union(intervals):
    total = 0
    left = right = None
    for start, end in sorted(intervals):
        if left is None:
            left, right = start, end
        elif start > right:
            total += right - left
            left, right = start, end
        else:
            right = max(right, end)
    if left is not None:
        total += right - left
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sqlite")
    ap.add_argument("--output", default="dense_down_results.json")
    ap.add_argument("--csv", default="dense_down_results.csv")
    ap.add_argument("--reference-js", default="sweep-data.js")
    ap.add_argument("--metadata")
    args = ap.parse_args()
    conn = sqlite3.connect(f"file:{Path(args.sqlite).resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    tables = {x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    def columns(table):
        return {x[1] for x in conn.execute(f'PRAGMA table_info("{table}")')}
    strings = {r[0]: r[1] for r in conn.execute("SELECT id,value FROM StringIds")}
    nc = columns("NVTX_EVENTS")
    ranges = []
    for r in conn.execute("SELECT * FROM NVTX_EVENTS WHERE end IS NOT NULL"):
        text = r["text"] if "text" in nc else None
        if not text and "textId" in nc:
            text = strings.get(r["textId"])
        if not isinstance(text, str):
            continue
        match = re.fullmatch(r"dense_down/m=(\d+)/sample=(\d+)", text)
        if match:
            ranges.append((int(match[1]), int(match[2]), r["start"], r["end"],
                           r["globalTid"] if "globalTid" in nc else None))
    if not ranges:
        raise RuntimeError("No dense_down NVTX sample ranges found")
    launch_apis = []
    for name in ("CUPTI_ACTIVITY_KIND_RUNTIME", "CUPTI_ACTIVITY_KIND_DRIVER"):
        if name not in tables:
            continue
        cc = columns(name)
        for r in conn.execute(f'SELECT * FROM "{name}"'):
            launch_apis.append((r["start"], r["end"], r["correlationId"],
                                r["globalTid"] if "globalTid" in cc else None))
    launch_apis.sort()
    launch_starts = [api[0] for api in launch_apis]
    kc = columns("CUPTI_ACTIVITY_KIND_KERNEL")
    kernels_by_corr = {}
    for r in conn.execute("SELECT * FROM CUPTI_ACTIVITY_KIND_KERNEL"):
        name_id = r["demangledName"] if "demangledName" in kc else r["shortName"]
        name = strings.get(name_id, str(name_id))
        kernel = {"start_ns": r["start"], "end_ns": r["end"], "name": name,
                  "duration_us": (r["end"] - r["start"]) / 1000,
                  "stream_id": r["streamId"] if "streamId" in kc else None}
        kernels_by_corr.setdefault(r["correlationId"], []).append(kernel)
    points = {}
    bad = []
    for m, sample, start, end, tid in sorted(ranges):
        lo = bisect.bisect_left(launch_starts, start)
        hi = bisect.bisect_left(launch_starts, end)
        correlations = {corr for a, b, corr, api_tid in launch_apis[lo:hi]
                        if tid is None or api_tid is None or tid == api_tid}
        unique = {}
        for corr in correlations:
            for kernel in kernels_by_corr.get(corr, []):
                key = (kernel["start_ns"], kernel["end_ns"], kernel["name"], kernel["stream_id"])
                unique[key] = kernel
        kernels = sorted(unique.values(), key=lambda x: x["start_ns"])
        quant = [v for v in kernels if "per_token_group_quant" in v["name"]]
        # Require the pinned dense FP8 family, not merely any non-quant kernel.
        gemm = [v for v in kernels if "sm100_fp8_fp4_gemm_1d1d_impl" in v["name"]]
        if len(kernels) != 2 or len(quant) != 1 or len(gemm) != 1:
            bad.append({"m": m, "sample": sample, "kernels": kernels,
                        "correlation_ids": sorted(correlations)})
            continue
        item = {"sample": sample,
                "active_union_us": interval_union([(v["start_ns"], v["end_ns"]) for v in kernels]) / 1000,
                "quant_us": quant[0]["duration_us"], "gemm_us": gemm[0]["duration_us"],
                "kernels": kernels}
        points.setdefault(m, []).append(item)
    baseline = {}
    ref = Path(args.reference_js)
    if ref.exists():
        for m, active in re.findall(r"^\s*\[(\d+),([\d.]+),", ref.read_text(), re.M):
            baseline[int(m)] = float(active)
    rows = []
    for m, samples in sorted(points.items()):
        values = [s["active_union_us"] for s in samples]
        median = statistics.median(values)
        row = {"m": m, "n": 6144, "k": 1536, "sample_count": len(samples),
               "active_union_median_us": median,
               "active_union_mean_us": statistics.mean(values),
               "active_union_min_us": min(values), "active_union_p90_us": quantile(values, .9),
               "quant_mean_us": statistics.mean(s["quant_us"] for s in samples),
               "gemm_mean_us": statistics.mean(s["gemm_us"] for s in samples),
               "baseline_gb300_median_us": baseline.get(m),
               "b300_over_gb300_ratio": median / baseline[m] if m in baseline else None,
               "samples": samples}
        rows.append(row)
    result = {"schema_version": "b300-dense-down-active-union-v1",
              "source_sqlite": Path(args.sqlite).name,
              "measurement": "GPU active interval union of exactly two correlation-owned kernels per NVTX range",
              "nvtx_range_count": len(ranges), "valid_sample_count": sum(len(x) for x in points.values()),
              "rejected_samples": bad, "points": rows}
    if args.metadata:
        result["run_metadata"] = json.loads(Path(args.metadata).read_text())
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    fields = [k for k in rows[0] if k != "samples"] if rows else []
    with open(args.csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: v for k, v in row.items() if k != "samples"})
    print(json.dumps({"ranges": len(ranges), "shapes": len(rows), "bad_samples": len(bad),
                      "output": args.output}))
    if bad:
        raise SystemExit("Rejected samples exist; inspect JSON before using these results")


if __name__ == "__main__":
    main()
