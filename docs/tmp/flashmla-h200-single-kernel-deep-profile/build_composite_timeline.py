#!/usr/bin/env python3
"""Build an evidence-tiered FlashMLA composite timeline.

The accepted scaffold contains CTA enter/exit plus WG2 tile begin/K-ready
landmarks. Future sparse probe sets can add a few WG0/WG1/WG2 landmarks per
build. This analyzer joins them by CTA identity and tile ordinal, checks shared
anchors, and emits an explicit *cross-run composite*. It never silently turns
separate launches into one cycle-exact trace.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


CTA_KEY_FIELDS = ("partition", "batch_idx", "block_idx")
TILE_KEY_FIELDS = ("partition", "ordinal", "batch_idx", "block_idx", "buf_idx")
REQUIRED_CSV_FIELDS = {
    "kind",
    "partition",
    "smid",
    "warpgroup",
    "ordinal",
    "batch_idx",
    "block_idx",
    "buf_idx",
    "event",
    "global_ns",
    "sm_cycles",
}


DETAIL_PHASE_PAIRS: dict[str, list[tuple[str, str, str, str]]] = {
    "WG0": [
        ("k_ready_wait", "TILE_BEGIN_K_WAIT_BEGIN", "K_READY", "wait"),
        ("qk_issue", "K_READY", "QK_ISSUED", "compute"),
        ("qk_completion", "QK_ISSUED", "QK_DONE", "compute"),
        ("score_buffer_wait", "QK_DONE", "SCOREBUF_FREE", "wait"),
        ("online_softmax", "SCOREBUF_FREE", "SOFTMAX_DONE", "compute"),
        ("score_publish", "SOFTMAX_DONE", "SCORE_PUBLISHED", "relay"),
        ("local_pv_issue", "SCORE_PUBLISHED", "LOCAL_PV_ISSUED", "compute"),
        ("score_ready_signal", "LOCAL_PV_ISSUED", "SCORE_READY_SIGNAL_DONE", "relay"),
        ("local_pv_completion", "SCORE_READY_SIGNAL_DONE", "LOCAL_PV_DONE", "compute"),
        ("k_release_and_tail", "LOCAL_PV_DONE", "TILE_END", "tail"),
    ],
    "WG1": [
        ("score_ready_wait", "TILE_BEGIN_SCORE_WAIT_BEGIN", "SCORE_READY", "wait"),
        ("accumulator_rescale", "SCORE_READY", "RESCALE_DONE", "compute"),
        ("remote_pv_issue", "RESCALE_DONE", "REMOTE_PV_ISSUED", "compute"),
        ("remote_pv_completion", "REMOTE_PV_ISSUED", "REMOTE_PV_DONE", "compute"),
        ("k_buffer_release", "REMOTE_PV_DONE", "KBUF_RELEASED", "relay"),
        ("score_buffer_release", "KBUF_RELEASED", "SCOREBUF_FREE_SIGNAL_DONE", "relay"),
        ("tile_tail", "SCOREBUF_FREE_SIGNAL_DONE", "TILE_END", "tail"),
    ],
    "WG2": [
        ("tile_prologue", "TILE_BEGIN", "R0_ADDR_BEGIN", "setup"),
        ("r0_address_index_scale", "R0_ADDR_BEGIN", "R0_INDEX_SCALE_READY", "address"),
        ("k_buffer_wait", "R0_INDEX_SCALE_READY", "KBUF_AVAILABLE", "wait"),
        ("r0_nope_gather_dequant", "KBUF_AVAILABLE", "R0_NOPE_GATHER_DEQUANT_DONE", "memory"),
        ("r0_rope_gather_store", "R0_NOPE_GATHER_DEQUANT_DONE", "R0_ROPE_DONE", "memory"),
        ("r1_address_begin", "R0_ROPE_DONE", "R1_ADDR_BEGIN", "address"),
        ("r1_address_index_scale", "R1_ADDR_BEGIN", "R1_INDEX_SCALE_READY", "address"),
        ("r1_nope_gather_dequant", "R1_INDEX_SCALE_READY", "R1_NOPE_GATHER_DEQUANT_DONE", "memory"),
        ("r1_rope_gather_store", "R1_NOPE_GATHER_DEQUANT_DONE", "R1_ROPE_DONE", "memory"),
        ("shared_fence", "R1_ROPE_DONE", "SMEM_FENCE_DONE", "relay"),
        ("validity_flags", "SMEM_FENCE_DONE", "VALIDITY_DONE", "setup"),
        ("k_ready_relay", "VALIDITY_DONE", "K_READY_SIGNAL_DONE_TILE_END", "relay"),
    ],
}


WG2_INTERNAL_PHASES = [
    ("tile_to_r0_index", "Tile entry → round-0 index/scales", "0", "2"),
    ("k_buffer_wait", "K-buffer wait", "2", "3"),
    ("r0_nope", "Round-0 NoPE gather/dequant", "3", "4"),
    ("r0_rope", "Round-0 RoPE gather/store", "4", "5"),
    ("r1_index", "Round-1 address/index/scales", "5", "7"),
    ("r1_nope", "Round-1 NoPE gather/dequant", "7", "8"),
    ("r1_rope", "Round-1 RoPE gather/store", "8", "9"),
    ("publish", "Fence, validity, K-ready publish", "9", "13"),
]

WG2_MECHANISM_EXPLANATIONS: dict[str, dict[str, str]] = {
    "tile_to_r0_index": {
        "short_label": "Round 0 · index, address, scales",
        "scope": "Prepare selected records 0–31",
        "family": "address_index_scales",
        "what_happens": "WG2 resolves selected token IDs to paged-KV addresses, prefetches the next sparse index, forms each cache-record pointer, and loads the four FP32 dequantization scales used by V32.",
        "data_movement": "Reads TopK index entries and scale metadata from global memory. The 512-value NoPE payload has not yet been gathered in this phase.",
        "share_meaning": "The relative share of the perturbed beat's pooled mean spent reaching the first round's index-and-scale-ready landmark.",
    },
    "k_buffer_wait": {
        "short_label": "K-buffer wait",
        "scope": "Wait before overwriting the rotating shared buffer",
        "family": "coordination",
        "what_happens": "WG2 waits on the transaction barrier until WG0 and WG1 have finished consuming the selected shared-memory K/V buffer slot.",
        "data_movement": "This is reuse coordination, not a bulk KV copy. It prevents the producer from overwriting a buffer that consumer warpgroups still read. Gen9 samples clustered at 0, 32, or 64 ns—near the captured timer granularity.",
        "share_meaning": "The buffer was usually already available in these perturbed Gen9 samples, but the sub-tick-sized share is resolution-limited. It does not prove that production waits by this percentage.",
    },
    "r0_nope": {
        "short_label": "Round 0 · NoPE gather/dequant",
        "scope": "Prepare selected records 0–31",
        "family": "nope",
        "what_happens": "For the first 32 selected records, WG2 gathers the non-positional latent in eight chunks, applies the previously loaded scales, converts FP8 values to BF16, and stores the result in the shared K/V layout.",
        "data_movement": "Across this 32-record round, it reads 16 KiB of unique FP8 NoPE payload from sparse cache addresses and expands that to 32 KiB of BF16 data in shared memory.",
        "share_meaning": "This was the largest single interval on the perturbed clock. Treat that as a strong source-inspection lead, not a production-time percentage.",
    },
    "r0_rope": {
        "short_label": "Round 0 · RoPE gather/store",
        "scope": "Prepare selected records 0–31",
        "family": "rope",
        "what_happens": "WG2 gathers the cached positional part for the first 32 records and stages it in shared memory. This kernel phase loads the RoPE-bearing values; it does not perform a new rotary transform here.",
        "data_movement": "Per selected record, it reads 64 BF16 positional values (128 bytes) and stores them unchanged into the shared K tile used by QK.",
        "share_meaning": "The relative mean share of first-round positional-field gathering on the perturbed Gen9 beat.",
    },
    "r1_index": {
        "short_label": "Round 1 · index, address, scales",
        "scope": "Prepare selected records 32–63",
        "family": "address_index_scales",
        "what_happens": "The producer advances to the second 32-record assignment, resolves its sparse indices to cache addresses, updates prefetched indices, and loads the scales for those records.",
        "data_movement": "Reads the second round's TopK index entries and scale metadata from global memory before its bulk latent gather.",
        "share_meaning": "The relative share of the perturbed mean spent preparing addresses and scales for records 32–63.",
    },
    "r1_nope": {
        "short_label": "Round 1 · NoPE gather/dequant",
        "scope": "Prepare selected records 32–63",
        "family": "nope",
        "what_happens": "WG2 repeats the sparse NoPE load, scale application, FP8-to-BF16 conversion, and shared-memory staging for the second 32 records.",
        "data_movement": "Across this second 32-record round, it again reads 16 KiB of unique FP8 NoPE payload and expands it to 32 KiB of BF16 data in the remaining shared K/V tile region.",
        "share_meaning": "The second large NoPE interval on the perturbed clock. Round-to-round differences may reflect cache/TLB state, scheduling, or the probe itself; they are not a production speedup or slowdown.",
    },
    "r1_rope": {
        "short_label": "Round 1 · RoPE gather/store",
        "scope": "Prepare selected records 32–63",
        "family": "rope",
        "what_happens": "WG2 gathers and stages the cached positional field for the second 32 records, completing the 64-record tile's RoPE-bearing K data.",
        "data_movement": "Reads 64 BF16 positional values (128 bytes) per selected record and writes them unchanged into shared memory.",
        "share_meaning": "The relative mean share of second-round positional-field gathering on the perturbed Gen9 beat.",
    },
    "publish": {
        "short_label": "Fence, validity, K-ready publish",
        "scope": "Make the complete 64-record tile consumable",
        "family": "coordination",
        "what_happens": "After both rounds, WG2 issues the shared-memory visibility fence, writes validity flags for selected indices, lane 0 performs its local K-ready barrier arrival, and the code flips the rotating buffer phase.",
        "data_movement": "No new bulk KV payload is gathered. This phase orders and publishes the shared data already written so WG0 and WG1 can safely consume it.",
        "share_meaning": "The perturbed mean share ending after lane 0's own K-ready arrival. E13 is not proof that every producer arrival completed or that consumers started or finished QK, softmax, or PV.",
    },
}

WG2_MECHANISM_FAMILY_LABELS = {
    "nope": "NoPE gather/dequant",
    "address_index_scales": "Address/index/scales",
    "rope": "RoPE gather/store",
    "coordination": "Buffer wait + publish",
}

WG2_CUMULATIVE_SCHEMA = (
    "flashmla-wg2-single-cta-cumulative-axis-analysis/v1"
)
WG2_FULL_AXIS_SCHEMA = (
    "flashmla-wg2-single-cta-same-launch-full-axis-analysis/v1"
)
WG2_GEN9_REJECTION_SCHEMA = "flashmla-wg2-gen9-full-axis-rejection/v1"
WG2_GEN13_REJECTION_SCHEMA = "flashmla-wg2-gen13-all-cta-register-pair-rejection/v1"
WG2_CUMULATIVE_ENDPOINT_IDS = [2, 3, 4, 5, 7, 8, 9, 13]
WG2_FULL_AXIS_EVENT_IDS = [0, 2, 3, 4, 5, 7, 8, 9, 13]


@dataclass(frozen=True)
class TraceRow:
    kind: str
    partition: int
    smid: int
    warpgroup: int
    ordinal: int
    batch_idx: int
    block_idx: int
    buf_idx: int
    event: str
    global_ns: int
    sm_cycles: int

    @property
    def cta_key(self) -> tuple[int, int, int]:
        return (self.partition, self.batch_idx, self.block_idx)

    @property
    def tile_key(self) -> tuple[int, int, int, int, int]:
        return (
            self.partition,
            self.ordinal,
            self.batch_idx,
            self.block_idx,
            self.buf_idx,
        )


def load_rows(path: Path) -> list[TraceRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_CSV_FIELDS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing CSV fields: {sorted(missing)}")
        rows = []
        for source in reader:
            rows.append(
                TraceRow(
                    kind=source["kind"],
                    partition=int(source["partition"]),
                    smid=int(source["smid"]),
                    warpgroup=int(source["warpgroup"]),
                    ordinal=int(source["ordinal"]),
                    batch_idx=int(source["batch_idx"]),
                    block_idx=int(source["block_idx"]),
                    buf_idx=int(source["buf_idx"]),
                    event=source["event"],
                    global_ns=int(source["global_ns"]),
                    sm_cycles=int(source["sm_cycles"]),
                )
            )
    return rows


def percentile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize(values: Iterable[float], suffix: str = "us") -> dict[str, Any]:
    numbers = list(values)
    if not numbers:
        return {"n": 0}
    return {
        "n": len(numbers),
        f"min_{suffix}": min(numbers),
        f"p50_{suffix}": percentile(numbers, 0.5),
        f"p90_{suffix}": percentile(numbers, 0.9),
        f"p99_{suffix}": percentile(numbers, 0.99),
        f"max_{suffix}": max(numbers),
        f"mean_{suffix}": statistics.fmean(numbers),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public_source_ref(path: Path) -> str:
    """Return a stable provenance label without publishing a workstation path."""
    resolved = path.resolve()
    parts = resolved.parts
    if "z_local" in parts:
        return "/".join(parts[parts.index("z_local") :])
    return resolved.name


def event_map(rows: Iterable[TraceRow]) -> dict[str, TraceRow]:
    result: dict[str, TraceRow] = {}
    for row in rows:
        if row.event in result:
            raise ValueError(
                f"duplicate event {row.event} for partition={row.partition}, "
                f"warpgroup={row.warpgroup}, ordinal={row.ordinal}"
            )
        result[row.event] = row
    return result


def scaffold_analysis(rows: list[TraceRow], manifest: dict[str, Any]) -> dict[str, Any]:
    config = manifest["accepted_scaffold"]
    cta_rows: dict[tuple[int, int, int], list[TraceRow]] = defaultdict(list)
    tile_rows: dict[tuple[int, int, int, int, int], list[TraceRow]] = defaultdict(list)
    for row in rows:
        if row.kind == "cta":
            cta_rows[row.cta_key].append(row)
        elif row.kind == "tile" and row.warpgroup == 2:
            tile_rows[row.tile_key].append(row)

    ctas: list[dict[str, Any]] = []
    cta_events_by_partition: dict[int, dict[str, TraceRow]] = {}
    for key, group in cta_rows.items():
        events = event_map(group)
        for required in config["required_cta_events"]:
            if required not in events:
                raise ValueError(f"CTA {key} lacks {required}")
        enter = events["CTA_ENTER"]
        exit_row = events["CTA_EXIT"]
        cta_events_by_partition[enter.partition] = events
        ctas.append(
            {
                "partition": enter.partition,
                "batch_idx": enter.batch_idx,
                "block_idx": enter.block_idx,
                "smid": enter.smid,
                "enter_ns": enter.global_ns,
                "exit_ns": exit_row.global_ns,
                "duration_us": (exit_row.global_ns - enter.global_ns) / 1000,
                "tile_count": 0,
            }
        )

    if len(ctas) != config["expected_ctas"]:
        raise ValueError(f"expected {config['expected_ctas']} CTAs, found {len(ctas)}")

    tiles_by_partition: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for key, group in tile_rows.items():
        events = event_map(group)
        for required in config["required_tile_events"]:
            if required not in events:
                raise ValueError(f"tile {key} lacks {required}")
        begin = events["TILE_BEGIN"]
        end = events["K_READY_SIGNAL_DONE_TILE_END"]
        if end.global_ns < begin.global_ns:
            raise ValueError(f"negative WG2 service interval for tile {key}")
        tiles_by_partition[begin.partition].append(
            {
                "ordinal": begin.ordinal,
                "batch_idx": begin.batch_idx,
                "block_idx": begin.block_idx,
                "buf_idx": begin.buf_idx,
                "begin_ns": begin.global_ns,
                "end_ns": end.global_ns,
                "duration_us": (end.global_ns - begin.global_ns) / 1000,
            }
        )

    cta_by_partition = {item["partition"]: item for item in ctas}
    for partition, tiles in tiles_by_partition.items():
        tiles.sort(key=lambda item: item["ordinal"])
        cta_by_partition[partition]["tile_count"] = len(tiles)

    histogram = Counter(item["tile_count"] for item in ctas)
    expected_histogram = {
        int(tile_count): count
        for tile_count, count in config["expected_tile_histogram"].items()
    }
    if dict(sorted(histogram.items())) != dict(sorted(expected_histogram.items())):
        raise ValueError(
            f"tile histogram mismatch: got {dict(histogram)}, expected {expected_histogram}"
        )

    launch_origin_ns = min(item["enter_ns"] for item in ctas)
    launch_end_ns = max(item["exit_ns"] for item in ctas)
    makespan_us = (launch_end_ns - launch_origin_ns) / 1000
    selected = sorted(
        (item for item in ctas if item["tile_count"] > 0),
        key=lambda item: (-item["tile_count"], -item["duration_us"], item["partition"]),
    )[0]
    selected_tiles = tiles_by_partition[selected["partition"]]
    selected_enter_ns = selected["enter_ns"]

    service_segments: list[dict[str, Any]] = []
    for tile in selected_tiles:
        service_segments.append(
            {
                "kind": "wg2_service",
                "ordinal": tile["ordinal"],
                "batch_idx": tile["batch_idx"],
                "block_idx": tile["block_idx"],
                "buf_idx": tile["buf_idx"],
                "start_us_from_cta": (tile["begin_ns"] - selected_enter_ns) / 1000,
                "end_us_from_cta": (tile["end_ns"] - selected_enter_ns) / 1000,
                "start_us_from_launch": (tile["begin_ns"] - launch_origin_ns) / 1000,
                "end_us_from_launch": (tile["end_ns"] - launch_origin_ns) / 1000,
                "duration_us": tile["duration_us"],
                "evidence": "accepted_low_overhead_absolute",
            }
        )

    before_first_us = service_segments[0]["start_us_from_cta"]
    service_union_us = sum(segment["duration_us"] for segment in service_segments)
    between_us = sum(
        service_segments[index + 1]["start_us_from_cta"]
        - service_segments[index]["end_us_from_cta"]
        for index in range(len(service_segments) - 1)
    )
    after_last_us = selected["duration_us"] - service_segments[-1]["end_us_from_cta"]
    cover_sum = before_first_us + service_union_us + between_us + after_last_us
    if abs(cover_sum - selected["duration_us"]) > 1e-9:
        raise ValueError("selected CTA observed-region accounting does not close")

    for item in ctas:
        item["start_us_from_launch"] = (item.pop("enter_ns") - launch_origin_ns) / 1000
        item["end_us_from_launch"] = (item.pop("exit_ns") - launch_origin_ns) / 1000
    ctas.sort(key=lambda item: item["partition"])

    return {
        "evidence_label": "accepted_low_overhead_absolute",
        "run_id": config["id"],
        "trace_overhead_pct": config["trace_overhead_pct"],
        "launch_origin": "minimum CTA_ENTER global_ns in this run",
        "makespan_us": makespan_us,
        "coverage": {
            "cta_count": len(ctas),
            "active_ctas": sum(item["tile_count"] > 0 for item in ctas),
            "no_work_ctas": sum(item["tile_count"] == 0 for item in ctas),
            "wg2_tile_count": sum(item["tile_count"] for item in ctas),
            "tile_histogram": {str(key): value for key, value in sorted(histogram.items())},
        },
        "active_cta_duration": summarize(
            [item["duration_us"] for item in ctas if item["tile_count"] > 0]
        ),
        "cta_start_skew_us": summarize([item["start_us_from_launch"] for item in ctas]),
        "all_ctas": ctas,
        "selected_critical_cta": {
            "selection": "maximum WG2 tile count, then longest CTA duration, then lowest partition",
            "partition": selected["partition"],
            "smid": selected["smid"],
            "batch_idx": selected["batch_idx"],
            "block_idx": selected["block_idx"],
            "start_us_from_launch": selected["start_us_from_launch"],
            "end_us_from_launch": selected["end_us_from_launch"],
            "duration_us": selected["duration_us"],
            "tile_count": selected["tile_count"],
            "observed_region_accounting": {
                "before_first_wg2_us": before_first_us,
                "wg2_service_union_us": service_union_us,
                "between_wg2_windows_us": between_us,
                "after_last_wg2_us": after_last_us,
                "wg2_service_fraction_of_cta": service_union_us / selected["duration_us"],
                "warning": "WG0/WG1 overlap these regions. Non-WG2 time is not GPU idle time and these values are not exclusive source-operation costs.",
            },
            "wg2_service_duration": summarize(
                [segment["duration_us"] for segment in service_segments]
            ),
            "wg2_service_segments": service_segments,
        },
        "source_checks": {
            "row_count": len(rows),
            "required_cta_events_present": True,
            "required_wg2_events_present": True,
            "tile_histogram_matches": True,
        },
    }


def detailed_reference_analysis(
    rows: list[TraceRow], manifest: dict[str, Any]
) -> dict[str, Any]:
    config = manifest["perturbed_reference"]
    partition = int(config["partition"])
    ordinal = int(config["representative_tile_ordinal"])
    selected = [row for row in rows if row.partition == partition]
    cta_enter_rows = [
        row for row in selected if row.kind == "cta" and row.event == "CTA_ENTER"
    ]
    cta_exit_rows = [
        row for row in selected if row.kind == "cta" and row.event == "CTA_EXIT"
    ]
    if len(cta_enter_rows) != 1 or len(cta_exit_rows) != 1:
        raise ValueError(
            f"detailed partition {partition} needs exactly one CTA_ENTER/CTA_EXIT"
        )
    cta_enter = cta_enter_rows[0]
    cta_exit = cta_exit_rows[0]
    enter = cta_enter.global_ns
    exit_ns = cta_exit.global_ns

    lane_segments: dict[str, list[dict[str, Any]]] = {}
    lane_spans: dict[str, list[dict[str, Any]]] = {}
    for lane, warpgroup in (("WG0", 0), ("WG1", 1), ("WG2", 2)):
        rows_by_ordinal: dict[int, list[TraceRow]] = defaultdict(list)
        for row in selected:
            if row.kind == "tile" and row.warpgroup == warpgroup:
                rows_by_ordinal[row.ordinal].append(row)
        if ordinal not in rows_by_ordinal:
            raise ValueError(f"detailed reference lacks {lane} tile {ordinal}")

        tile_events = event_map(rows_by_ordinal[ordinal])
        segments = []
        for phase, start_name, end_name, kind in DETAIL_PHASE_PAIRS[lane]:
            if start_name not in tile_events or end_name not in tile_events:
                raise ValueError(
                    f"detailed reference {lane} tile {ordinal} lacks {start_name}/{end_name}"
                )
            start = (tile_events[start_name].global_ns - enter) / 1000
            end = (tile_events[end_name].global_ns - enter) / 1000
            segments.append(
                {
                    "phase": phase,
                    "kind": kind,
                    "start_us_from_cta": start,
                    "end_us_from_cta": end,
                    "duration_us": end - start,
                }
            )
        lane_segments[lane] = segments

        spans = []
        full_pair = {
            "WG0": ("TILE_BEGIN_K_WAIT_BEGIN", "TILE_END"),
            "WG1": ("TILE_BEGIN_SCORE_WAIT_BEGIN", "TILE_END"),
            "WG2": ("TILE_BEGIN", "K_READY_SIGNAL_DONE_TILE_END"),
        }[lane]
        for tile_ordinal, group in sorted(rows_by_ordinal.items()):
            events = event_map(group)
            start = (events[full_pair[0]].global_ns - enter) / 1000
            end = (events[full_pair[1]].global_ns - enter) / 1000
            spans.append(
                {
                    "ordinal": tile_ordinal,
                    "start_us_from_cta": start,
                    "end_us_from_cta": end,
                    "duration_us": end - start,
                }
            )
        lane_spans[lane] = spans

    return {
        "evidence_label": "high_detail_perturbed_mechanism_only",
        "run_id": config["id"],
        "partition": partition,
        "smid": cta_enter.smid,
        "cta_duration_us": (exit_ns - enter) / 1000,
        "representative_tile_ordinal": ordinal,
        "trace_overhead_pct": config["trace_overhead_pct"],
        "absolute_transfer_allowed": bool(config["absolute_transfer_allowed"]),
        "lane_segments": lane_segments,
        "all_tile_lane_spans": lane_spans,
        "warning": "These timestamps are exact for the perturbed trace, but their microseconds cannot be transferred to the accepted ~100 us scaffold.",
    }


def index_scaffold_anchors(rows: list[TraceRow]) -> dict[tuple[Any, ...], TraceRow]:
    anchors: dict[tuple[Any, ...], TraceRow] = {}
    for row in rows:
        if row.event in {"CTA_ENTER", "CTA_EXIT"}:
            key = ("cta",) + row.cta_key + (row.event,)
        elif row.warpgroup == 2 and row.event in {
            "TILE_BEGIN",
            "K_READY_SIGNAL_DONE_TILE_END",
        }:
            key = ("tile",) + row.tile_key + (row.event,)
        else:
            continue
        anchors[key] = row
    return anchors


def analyze_sparse_probe(
    spec: dict[str, Any],
    manifest_dir: Path,
    scaffold_rows: list[TraceRow],
    scaffold: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "id": spec["id"],
        "lane": spec["lane"],
        "requested_status": spec["status"],
        "required_target_events": spec["required_target_events"],
        "shared_anchor_events": spec["shared_anchor_events"],
    }
    if not spec.get("path"):
        return {
            **base,
            "status": "pending_measurement",
            "alignment_accepted": False,
            "reason": "No trace CSV is assigned yet.",
            "aligned_intervals": [],
        }

    path = (manifest_dir / spec["path"]).resolve()
    if not path.exists():
        return {
            **base,
            "status": "missing_file",
            "alignment_accepted": False,
            "reason": f"Configured trace CSV does not exist: {spec['path']}",
            "aligned_intervals": [],
        }

    rows = load_rows(path)
    scaffold_anchors = index_scaffold_anchors(scaffold_rows)
    probe_anchors = index_scaffold_anchors(rows)
    requested_anchor_events = set(spec["shared_anchor_events"])
    common_keys = sorted(
        key
        for key in set(scaffold_anchors) & set(probe_anchors)
        if key[-1] in requested_anchor_events
    )
    residuals_us: list[float] = []
    for key in common_keys:
        scaffold_row = scaffold_anchors[key]
        probe_row = probe_anchors[key]
        cta_partition = key[1]
        scaffold_cta_enter = next(
            value
            for anchor_key, value in scaffold_anchors.items()
            if anchor_key[0] == "cta"
            and anchor_key[1] == cta_partition
            and anchor_key[-1] == "CTA_ENTER"
        )
        probe_cta_enter = next(
            value
            for anchor_key, value in probe_anchors.items()
            if anchor_key[0] == "cta"
            and anchor_key[1] == cta_partition
            and anchor_key[-1] == "CTA_ENTER"
        )
        residuals_us.append(
            (
                (probe_row.global_ns - probe_cta_enter.global_ns)
                - (scaffold_row.global_ns - scaffold_cta_enter.global_ns)
            )
            / 1000
        )

    selected_partition = scaffold["selected_critical_cta"]["partition"]
    selected_cta = scaffold["selected_critical_cta"]
    target_rows = [
        row
        for row in rows
        if row.partition == selected_partition
        and row.event in set(spec["required_target_events"])
    ]
    missing_targets = sorted(set(spec["required_target_events"]) - {row.event for row in target_rows})

    scaffold_cta_pairs: dict[tuple[int, int, int], dict[str, TraceRow]] = defaultdict(dict)
    probe_cta_pairs: dict[tuple[int, int, int], dict[str, TraceRow]] = defaultdict(dict)
    for row in scaffold_rows:
        if row.kind == "cta" and row.event in {"CTA_ENTER", "CTA_EXIT"}:
            scaffold_cta_pairs[row.cta_key][row.event] = row
    for row in rows:
        if row.kind == "cta" and row.event in {"CTA_ENTER", "CTA_EXIT"}:
            probe_cta_pairs[row.cta_key][row.event] = row
    cta_duration_delta_pct: list[float] = []
    for key in sorted(set(scaffold_cta_pairs) & set(probe_cta_pairs)):
        left = scaffold_cta_pairs[key]
        right = probe_cta_pairs[key]
        if set(left) != {"CTA_ENTER", "CTA_EXIT"} or set(right) != {"CTA_ENTER", "CTA_EXIT"}:
            continue
        scaffold_duration = left["CTA_EXIT"].global_ns - left["CTA_ENTER"].global_ns
        probe_duration = right["CTA_EXIT"].global_ns - right["CTA_ENTER"].global_ns
        if scaffold_duration > 0:
            cta_duration_delta_pct.append(
                100 * (probe_duration - scaffold_duration) / scaffold_duration
            )

    target_counts = Counter(row.event for row in target_rows)
    if spec["lane"] in {"WG0", "WG1", "WG2"}:
        expected_target_count = selected_cta["tile_count"]
    else:
        expected_target_count = 1
    incomplete_target_counts = {
        event: target_counts.get(event, 0)
        for event in spec["required_target_events"]
        if target_counts.get(event, 0) < expected_target_count
    }

    max_anchor_residual = max((abs(value) for value in residuals_us), default=math.inf)
    max_cta_duration_delta_pct = max(
        (abs(value) for value in cta_duration_delta_pct), default=math.inf
    )
    alignment_accepted = (
        not missing_targets
        and not incomplete_target_counts
        and bool(common_keys)
        and max_anchor_residual <= float(policy["max_shared_anchor_residual_us"])
        and max_cta_duration_delta_pct <= float(policy["max_cta_duration_delta_pct"])
    )

    aligned_points: list[dict[str, Any]] = []
    aligned_intervals: list[dict[str, Any]] = []
    if alignment_accepted:
        scaffold_launch_origin_ns = min(
            row.global_ns
            for row in scaffold_rows
            if row.kind == "cta" and row.event == "CTA_ENTER"
        )
        if spec["lane"] == "CTA":
            probe_enter = next(
                row
                for row in rows
                if row.partition == selected_partition
                and row.kind == "cta"
                and row.event == "CTA_ENTER"
            )
            for target in sorted(target_rows, key=lambda row: row.global_ns):
                aligned_points.append(
                    {
                        "lane": spec["lane"],
                        "event": target.event,
                        "warpgroup": target.warpgroup,
                        "time_us_from_launch": selected_cta["start_us_from_launch"]
                        + (target.global_ns - probe_enter.global_ns) / 1000,
                        "alignment_anchor": "CTA_ENTER",
                    }
                )
        else:
            scaffold_tile_anchors = {
                key: value
                for key, value in scaffold_anchors.items()
                if key[0] == "tile" and key[-1] in requested_anchor_events
            }
            probe_tile_anchors = {
                key: value
                for key, value in probe_anchors.items()
                if key[0] == "tile" and key[-1] in requested_anchor_events
            }
            targets_by_tile: dict[tuple[int, int, int, int, int], list[TraceRow]] = defaultdict(list)
            for target in target_rows:
                targets_by_tile[target.tile_key].append(target)
            for tile_key, targets in sorted(targets_by_tile.items()):
                candidate_anchors: list[tuple[TraceRow, TraceRow]] = []
                for anchor_event in requested_anchor_events:
                    key = ("tile",) + tile_key + (anchor_event,)
                    if key in scaffold_tile_anchors and key in probe_tile_anchors:
                        candidate_anchors.append(
                            (probe_tile_anchors[key], scaffold_tile_anchors[key])
                        )
                if not candidate_anchors:
                    continue
                for target in sorted(targets, key=lambda row: row.global_ns):
                    probe_anchor, scaffold_anchor = min(
                        candidate_anchors,
                        key=lambda pair: abs(target.global_ns - pair[0].global_ns),
                    )
                    aligned_points.append(
                        {
                            "lane": spec["lane"],
                            "partition": target.partition,
                            "ordinal": target.ordinal,
                            "batch_idx": target.batch_idx,
                            "block_idx": target.block_idx,
                            "buf_idx": target.buf_idx,
                            "event": target.event,
                            "time_us_from_launch": (
                                scaffold_anchor.global_ns - scaffold_launch_origin_ns
                            )
                            / 1000
                            + (target.global_ns - probe_anchor.global_ns) / 1000,
                            "alignment_anchor": probe_anchor.event,
                        }
                    )

        points_by_identity: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for point in aligned_points:
            if spec["lane"] == "CTA":
                key = (point.get("warpgroup", -1),)
            else:
                key = (
                    point["partition"],
                    point["ordinal"],
                    point["batch_idx"],
                    point["block_idx"],
                    point["buf_idx"],
                )
            points_by_identity[key].append(point)
        required_order = {event: index for index, event in enumerate(spec["required_target_events"])}
        for key, points in sorted(points_by_identity.items(), key=lambda item: str(item[0])):
            by_event = {point["event"]: point for point in points}
            present = sorted(
                (event for event in required_order if event in by_event),
                key=lambda event: required_order[event],
            )
            for start_event, end_event in zip(present, present[1:]):
                start = by_event[start_event]
                end = by_event[end_event]
                if end["time_us_from_launch"] < start["time_us_from_launch"]:
                    continue
                aligned_intervals.append(
                    {
                        "lane": spec["lane"],
                        "identity": list(key),
                        "phase": f"{start_event}_to_{end_event}",
                        "start_event": start_event,
                        "end_event": end_event,
                        "start_us_from_launch": start["time_us_from_launch"],
                        "end_us_from_launch": end["time_us_from_launch"],
                        "duration_us": end["time_us_from_launch"]
                        - start["time_us_from_launch"],
                        "evidence": "aligned_sparse_probe_cross_run_composite",
                    }
                )
    return {
        **base,
        "status": "measured" if alignment_accepted else "rejected_alignment",
        "alignment_accepted": alignment_accepted,
        "source": public_source_ref(path),
        "source_sha256": sha256(path),
        "row_count": len(rows),
        "common_anchor_count": len(common_keys),
        "anchor_residual_us": summarize(residuals_us),
        "max_absolute_anchor_residual_us": max_anchor_residual,
        "cta_duration_delta_pct": summarize(cta_duration_delta_pct, suffix="pct"),
        "max_absolute_cta_duration_delta_pct": max_cta_duration_delta_pct,
        "missing_target_events_for_selected_cta": missing_targets,
        "incomplete_target_event_counts_for_selected_cta": incomplete_target_counts,
        "aligned_event_points": aligned_points,
        "aligned_intervals": aligned_intervals,
        "reason": (
            "Shared-anchor and CTA-duration checks passed; intervals are aligned as a labeled cross-run composite."
            if alignment_accepted
            else "The probe is not composable until all targets exist and shared-anchor residuals pass."
        ),
    }


def load_accepted_probe_analysis(path: Path) -> dict[str, Any]:
    """Keep the page-facing accepted evidence, not every raw distribution."""
    source = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "page_ready_findings",
        "cta_partition_65",
        "stitched_partition_65_timeline",
        "same_launch_relays",
        "overhead_and_envelope_caveats",
        "validation",
    }
    missing = required - set(source)
    if missing:
        raise ValueError(f"{path}: accepted analysis lacks {sorted(missing)}")
    validation = source["validation"]
    run_count = sum(len(value["runs"]) for value in validation.values())
    if run_count != 39 or not all(
        value.get("all_three_repeats_pass") for value in validation.values()
    ):
        raise ValueError(
            f"{path}: expected all 39 accepted runs to pass, found {run_count}"
        )
    return {
        "source": public_source_ref(path),
        "source_sha256": sha256(path),
        "generated_at": source.get("generated_at"),
        "scope": source.get("scope", {}),
        "validation_summary": source["page_ready_findings"]["validation"],
        "page_ready_findings": source["page_ready_findings"],
        "cta_partition_65": source["cta_partition_65"],
        "stitched_partition_65_timeline": source[
            "stitched_partition_65_timeline"
        ],
        "same_launch_relays": source["same_launch_relays"],
        "overhead_and_envelope_caveats": source[
            "overhead_and_envelope_caveats"
        ],
        "accepted_probe_count": len(validation),
        "accepted_run_count": run_count,
    }


def load_wg2_microscope_outer_reference(
    manifest_dir: Path, config: dict[str, Any]
) -> dict[str, Any]:
    """Measure the independent outer producer beat at the microscope target."""
    partition = int(config["partition"])
    ordinal = int(config["ordinal"])
    expected_tile_count = int(config["partition_tile_count"])
    durations = []
    repeat_points = []
    sources = []
    for repeat, relative in enumerate(config["paths"], 1):
        path = (manifest_dir / relative).resolve()
        rows = load_rows(path)
        partition_tiles = {
            row.ordinal
            for row in rows
            if row.kind == "tile"
            and row.warpgroup == 2
            and row.partition == partition
            and row.event == "TILE_BEGIN"
        }
        if len(partition_tiles) != expected_tile_count:
            raise ValueError(
                f"{path}: partition {partition} expected {expected_tile_count} "
                f"tiles, got {len(partition_tiles)}"
            )
        events = {
            row.event: row
            for row in rows
            if row.kind == "tile"
            and row.warpgroup == 2
            and row.partition == partition
            and row.ordinal == ordinal
        }
        required = {"TILE_BEGIN", "K_READY_SIGNAL_DONE_TILE_END"}
        if not required <= set(events):
            raise ValueError(f"{path}: microscope target lacks {sorted(required)}")
        duration = (
            events["K_READY_SIGNAL_DONE_TILE_END"].global_ns
            - events["TILE_BEGIN"].global_ns
        ) / 1000
        if duration < 0:
            raise ValueError(f"{path}: negative microscope outer duration")
        durations.append(duration)
        repeat_points.append({"repeat": repeat, "duration_us": duration})
        sources.append(
            {"path": public_source_ref(path), "sha256": sha256(path)}
        )
    return {
        "partition": partition,
        "ordinal": ordinal,
        "partition_tile_count": expected_tile_count,
        "description": config["description"],
        "duration_us": {
            "count": len(durations),
            "median_us": statistics.median(durations),
            "min_us": min(durations),
            "max_us": max(durations),
        },
        "repeat_points": repeat_points,
        "sources": sources,
    }


def load_rejected_gen9_mechanistic_shape(path: Path) -> dict[str, Any]:
    """Load only a dimensionless mechanism shape from rejected Gen9.

    Gen9 is useful because all nine landmarks were captured in the same lane,
    tile, binary, and launch, and every sample closes exactly.  It is *not* an
    accepted timing source: all repeats incurred roughly 30 percent overhead.
    The public payload therefore receives normalized shares of pooled phase
    means, never the rejected absolute phase durations.
    """

    source = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if source.get("schema_version") != WG2_GEN9_REJECTION_SCHEMA:
        errors.append("wrong Gen9 rejection schema")
    if source.get("status") != "rejected" or source.get("analysis_status") != "rejected":
        errors.append("Gen9 is not marked rejected")

    experiment = source.get("experiment") or {}
    if experiment.get("event_ids") != WG2_FULL_AXIS_EVENT_IDS:
        errors.append("Gen9 event axis is wrong")
    if experiment.get("repeats") != 3 or experiment.get("samples_per_repeat") != 100:
        errors.append("Gen9 repeat/sample contract is wrong")

    validated = source.get("validated_passes") or {}
    for field in (
        "all_runs_bitwise_correct",
        "all_runs_reference_correct",
        "all_runs_exact_target_coverage",
        "all_runs_zero_overflow",
        "all_300_samples_monotonic",
        "all_300_samples_exact_integer_closure",
    ):
        if validated.get(field) is not True:
            errors.append(f"Gen9 validation failed: {field}")

    rejection = source.get("rejection") or {}
    overhead_gate = float(rejection.get("overhead_gate_pct", math.nan))
    repeat_overheads = rejection.get("repeat_overheads") or []
    if overhead_gate != 5.0 or len(repeat_overheads) != 3:
        errors.append("Gen9 overhead-gate contract is wrong")
    for repeat in repeat_overheads:
        if (
            float(repeat.get("median_overhead_pct", -math.inf)) <= overhead_gate
            or float(repeat.get("p90_overhead_pct", -math.inf)) <= overhead_gate
            or repeat.get("median_gate_pass") is not False
            or repeat.get("p90_gate_pass") is not False
        ):
            errors.append("Gen9 repeat was not rejected by both overhead gates")

    disposition = source.get("disposition") or {}
    for field in (
        "accepted_for_phase_attribution",
        "accepted_for_timeline_rendering",
        "accepted_as_low_overhead_measurement",
        "rescaled",
        "corrected_for_observer_effect",
    ):
        if disposition.get(field) is not False:
            errors.append(f"unsafe Gen9 disposition: {field}")

    measurements = source.get("mechanistic_measurements_not_accepted_for_attribution") or {}
    raw_segments = measurements.get("segments") or []
    expected = [(key, label, int(start), int(end)) for key, label, start, end in WG2_INTERNAL_PHASES]
    if len(raw_segments) != len(expected):
        errors.append("Gen9 segment count is wrong")
    pooled_means: list[float] = []
    normalized_segments: list[dict[str, Any]] = []
    for index, expected_phase in enumerate(expected):
        if index >= len(raw_segments):
            break
        item = raw_segments[index]
        key, label, start_event, end_event = expected_phase
        if (
            item.get("key") != key
            or item.get("label") != label
            or item.get("start_event_id") != start_event
            or item.get("end_event_id") != end_event
            or item.get("measurement_semantics") != "direct_same_launch_difference"
            or item.get("disposition") != "mechanistic_only_due_observer_effect"
            or item.get("n") != 300
        ):
            errors.append(f"Gen9 segment contract failed: {key}")
            continue
        mean_us = float(item.get("mean_us", math.nan))
        if not math.isfinite(mean_us) or mean_us < 0:
            errors.append(f"Gen9 segment mean is invalid: {key}")
            continue
        pooled_means.append(mean_us)
        normalized_segments.append(
            {
                "key": key,
                "label": label,
                "start_event_id": start_event,
                "end_event_id": end_event,
                "sample_count": 300,
                **WG2_MECHANISM_EXPLANATIONS[key],
            }
        )

    total = measurements.get("total") or {}
    total_mean = float(total.get("mean_us", math.nan))
    closure = measurements.get("closure") or {}
    if (
        not math.isfinite(total_mean)
        or total_mean <= 0
        or total.get("n") != 300
        or total.get("disposition") != "mechanistic_only_due_observer_effect"
        or closure.get("residual_count") != 300
        or closure.get("max_abs_residual_ns") != 0
        or closure.get("passes") is not True
    ):
        errors.append("Gen9 total/closure contract failed")
    if pooled_means and not math.isclose(sum(pooled_means), total_mean, abs_tol=1e-12):
        errors.append("Gen9 pooled phase means do not close to the pooled total mean")
    if errors:
        raise ValueError(f"{path}: rejected Gen9 mechanism-shape validation failed: {errors}")

    for item, phase_mean in zip(normalized_segments, pooled_means):
        item["normalized_share_pct"] = 100.0 * phase_mean / total_mean
    if not math.isclose(
        sum(item["normalized_share_pct"] for item in normalized_segments),
        100.0,
        abs_tol=1e-9,
    ):
        raise ValueError(f"{path}: normalized Gen9 shares do not close to 100 percent")

    family_shares = []
    for family, label in WG2_MECHANISM_FAMILY_LABELS.items():
        share = sum(
            item["normalized_share_pct"]
            for item in normalized_segments
            if item["family"] == family
        )
        family_shares.append(
            {"key": family, "label": label, "normalized_share_pct": share}
        )
    if not math.isclose(
        sum(item["normalized_share_pct"] for item in family_shares),
        100.0,
        abs_tol=1e-9,
    ):
        raise ValueError(f"{path}: normalized Gen9 family shares do not close")

    compile_evidence = source.get("compile_evidence") or {}
    trace_symbol = compile_evidence.get("trace_symbol") or {}
    normal_symbol = compile_evidence.get("normal_symbol") or {}
    return {
        "status": "rejected_timing_mechanism_shape_only",
        "source": public_source_ref(path),
        "probe": "Gen9 same-launch nine-landmark global-timer axis",
        "overhead_gate_pct": overhead_gate,
        "repeat_overheads_pct": [
            {
                "repeat": int(item["repeat"]),
                "median": float(item["median_overhead_pct"]),
                "p90": float(item["p90_overhead_pct"]),
            }
            for item in repeat_overheads
        ],
        "samples": 300,
        "selected_context": {
            "partition": 1,
            "warpgroup": 2,
            "lane_in_warpgroup": 0,
            "tile_ordinal": 14,
            "cta_tile_count": 24,
            "event_span": "E0 TILE_BEGIN to E13 K_READY_SIGNAL_DONE_TILE_END",
        },
        "normalization": "share_of_sum_of_pooled_direct_phase_means_on_perturbed_clock",
        "normalization_explanation": {
            "denominator": "The denominator is the pooled E0-to-E13 mean for Gen9's selected partition-1, WG2 lane-0, ordinal-14 beat inside a non-straggler 24-tile CTA. It is defined as 100% for this inset only—not the whole kernel, the critical CTA, the 29 producer beats, or their 91.456-microsecond union.",
            "why_means_close": "Every sample partitions the same event-0-to-event-13 beat into eight adjacent intervals with exact integer-nanosecond closure. Arithmetic means preserve addition, so the eight pooled phase means sum to the pooled whole-beat mean and their shares sum to 100%.",
            "why_not_medians": "A separate median for each phase can come from a different sample. Marginal medians are not additive, so their sum need not equal the median whole beat; they are unsuitable for a closed composition bar.",
            "not_the_denominator": "The denominator is not the accepted approximately 3-microsecond outer beat, the direct 91.456-microsecond 29-window union, or the approximately 103-microsecond main-kernel duration.",
        },
        "two_round_geometry": {
            "tile_records": 64,
            "round_records": 32,
            "rounds": 2,
            "explanation": "On this H64 path, WG2's four producer warps prepare one 64-record tile in two 32-record rounds. Each round performs address/index/scale preparation, then NoPE gather/dequant, then RoPE gather/store. The plotted round difference is observed only on the perturbed clock; cache/TLB state, scheduling, and probe effects can all contribute, so it is not evidence that either round is intrinsically faster.",
        },
        "segments": normalized_segments,
        "family_shares": family_shares,
        "shares_close_pct": sum(
            item["normalized_share_pct"] for item in normalized_segments
        ),
        "all_samples_monotonic_and_exact_integer_closure": True,
        "compile_resources_match_normal": trace_symbol == normal_symbol,
        "absolute_phase_us_available_to_page": False,
        "production_clock_rescaling_allowed": False,
        "observer_boundary": {
            "invalidates": [
                "Absolute phase durations and any conversion of these shares into production microseconds.",
                "Claims that production spends an exact percentage in NoPE, RoPE, indexing, waiting, or publishing.",
                "Multiplying a segment share by the accepted outer beat, the 91.456-microsecond union, or the main-kernel duration.",
                "Interpreting the round-0 versus round-1 difference as an intrinsic speedup, slowdown, cache effect, or production asymmetry.",
            ],
            "still_supports": [
                "The source order: address/index/scales, optional buffer wait, NoPE gather/dequant, RoPE gather/store, second round, then fence/validity/publish.",
                "A qualitative optimization hypothesis: NoPE gather/dequant is the largest relative component on the instrumented path, followed by address/index/scale preparation.",
                "Direct same-launch event ordering and exact phase-to-whole closure for all 300 perturbed samples.",
            ],
        },
        "glossary": [
            {
                "term": "WG2",
                "definition": "The 128-thread producer warpgroup. It follows sparse addresses and prepares the next 64-record K/V tile while WG0 and WG1 consume other pipeline work.",
            },
            {
                "term": "NoPE",
                "definition": "The non-positional MLA latent. For each selected V32 cache record, WG2 gathers 512 FP8 values, applies four scales, converts them to BF16, and stages them for K/V use.",
            },
            {
                "term": "RoPE field",
                "definition": "The cached positional part used by QK: 64 BF16 values, or 128 bytes, per selected record. This producer phase loads and stages that field; it does not apply a new rotary transform.",
            },
            {
                "term": "K-buffer wait",
                "definition": "A transaction-barrier wait before WG2 reuses a rotating shared-memory K/V slot. The wait ends only after consumer warpgroups release that slot.",
            },
            {
                "term": "Fence + publish",
                "definition": "A shared-memory visibility fence, validity-flag write, and K-ready barrier arrival. The E13 timestamp is lane 0 after its own arrival, not a timestamp proving all producer arrivals or later consumer work are complete.",
            },
        ],
        "interpretation": "This inset preserves event order and a dimensionless phase-shape hypothesis only. It is not an accepted production-time decomposition and is neither rescaled nor observer-corrected.",
    }


def load_gen13_stop_record(path: Path) -> dict[str, Any]:
    """Validate the final, least-intrusive source-probe rejection."""

    source = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if source.get("schema_version") != WG2_GEN13_REJECTION_SCHEMA:
        errors.append("wrong Gen13 rejection schema")
    if source.get("status") != "rejected" or source.get("analysis_status") != "rejected":
        errors.append("Gen13 is not marked rejected")
    experiment = source.get("experiment") or {}
    if (
        experiment.get("events") != [3, 4]
        or experiment.get("final_launch_direct_pairs") != 125
        or len(experiment.get("eligible_partitions") or []) != 125
        or experiment.get("measurement_design")
        != "all_125_eligible_ctas_ordinal14_two_clock32_scalar_registers_deferred_flush"
    ):
        errors.append("Gen13 target/coverage contract is wrong")
    validated = source.get("validated_passes") or {}
    if not validated or not all(value is True for value in validated.values()):
        errors.append("Gen13 correctness/coverage validation failed")
    rejection = source.get("rejection") or {}
    median_overhead = float(rejection.get("median_overhead_pct", math.nan))
    p90_overhead = float(rejection.get("p90_overhead_pct", math.nan))
    if (
        float(rejection.get("overhead_gate_pct", math.nan)) != 5.0
        or not math.isfinite(median_overhead)
        or not math.isfinite(p90_overhead)
        or median_overhead <= 5.0
        or p90_overhead <= 5.0
        or rejection.get("median_gate_pass") is not False
        or rejection.get("p90_gate_pass") is not False
    ):
        errors.append("Gen13 did not fail both overhead gates as required")
    disposition = source.get("disposition") or {}
    for field in (
        "accepted_for_phase_attribution",
        "accepted_for_timeline_rendering",
        "accepted_as_low_overhead_measurement",
        "rescaled",
        "observer_effect_corrected",
    ):
        if disposition.get(field) is not False:
            errors.append(f"unsafe Gen13 disposition: {field}")
    if disposition.get("experiment_stop_condition") != "no further intrusive phase probes":
        errors.append("Gen13 stop condition is absent")
    compile_evidence = source.get("compile_evidence") or {}
    trace = compile_evidence.get("trace_symbol") or {}
    normal = compile_evidence.get("normal_symbol") or {}
    resource_fields = (
        "registers",
        "barriers",
        "stack_frame_bytes",
        "spill_store_bytes",
        "spill_load_bytes",
    )
    if any(trace.get(field) != normal.get(field) for field in resource_fields):
        errors.append("Gen13 trace/normal compile resources differ")
    resource_equivalence = compile_evidence.get("resource_equivalence") or {}
    if (
        resource_equivalence.get("register_count_equal") is not True
        or resource_equivalence.get("barrier_count_equal") is not True
        or resource_equivalence.get("both_zero_stack_and_spills") is not True
        or resource_equivalence.get("shared_memory_delta_vs_gen12_bytes") != 0
    ):
        errors.append("Gen13 resource-equivalence contract failed")
    if errors:
        raise ValueError(f"{path}: Gen13 stop-record validation failed: {errors}")
    return {
        "status": "rejected_stop_condition",
        "source": public_source_ref(path),
        "probe": "two clock32 scalar registers at E3/E4; deferred post-loop flush",
        "direct_pair_count": 125,
        "median_overhead_pct": median_overhead,
        "p90_overhead_pct": p90_overhead,
        "overhead_gate_pct": 5.0,
        "correctness_coverage_and_wrap_safety_pass": True,
        "compile_resources": {
            field: trace[field] for field in resource_fields
        },
        "shared_memory_plan_bytes": resource_equivalence["shared_memory_plan_bytes"],
        "shared_memory_delta_bytes": resource_equivalence[
            "shared_memory_delta_vs_gen12_bytes"
        ],
        "phase_duration_exposed_to_page": False,
        "experiment_stop_condition": disposition["experiment_stop_condition"],
    }


def normalize_optional_wg2_internal(path: Path) -> dict[str, Any]:
    """Normalize the optional eight selected steady-tile sparse-pair result.

    The compact input contract is intentionally simple::

      {"phases": [{"key": "tile_to_r0_index", "median_us": 0.5,
                    "p25_us": 0.4, "p75_us": 0.6,
                    "all_runtime_gates_pass": true}, ...]}

    No phase is rendered on the accepted clock unless all eight are present and
    explicitly pass.  Rejected generations remain page evidence, never phase
    attribution.
    """
    if not path.exists():
        return {
            "status": "unresolved_measurement_limit",
            "phases": [],
            "reason": "The completed source-probe ladder produced no absolute WG2 internal split below the 5% observer-overhead gate.",
        }
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("schema_version") == WG2_FULL_AXIS_SCHEMA:
        return normalize_wg2_full_axis(path, source)
    if source.get("schema_version") == WG2_CUMULATIVE_SCHEMA:
        return normalize_wg2_cumulative_axis(path, source)
    by_key = {item.get("key"): item for item in source.get("phases", [])}
    phases = []
    errors = []
    if source.get("status") != "accepted":
        errors.append("top-level status is not accepted")
    if (
        source.get("schema_version")
        != "flashmla-wg2-single-cta-steady-tile-phase-analysis/v1"
    ):
        errors.append("not the final generation-7 compact schema")
    if (
        source.get("measurement_design")
        != "repeated_single_cta_microscope_warmed_symbol_blocks"
    ):
        errors.append("not the warmed-symbol-block microscope design")
    if source.get("selected_partition") != 1:
        errors.append("selected partition is not 1")
    if source.get("selected_ordinal") != 14:
        errors.append("selected ordinal is not 14")
    if source.get("expected_samples_per_repeat") != 100:
        errors.append("expected samples per repeat is not 100")
    if source.get("repeats_per_phase") != 3:
        errors.append("repeats per phase is not 3")
    protocol = source.get("timing_protocol") or {}
    if protocol.get("name") != "warmed_symbol_blocks_v1":
        errors.append("timing protocol is not warmed_symbol_blocks_v1")
    if protocol.get("block_warmups") != 30:
        errors.append("timing protocol does not use 30 block warmups")
    if protocol.get("iterations_per_symbol") != 100:
        errors.append("timing protocol does not use 100 iterations per symbol")
    if protocol.get("repeat_orders") != [
        "control-first",
        "trace-first",
        "control-first",
    ]:
        errors.append("timing protocol does not use the accepted repeat order")
    acceptance = source.get("acceptance") or {}
    if acceptance.get("accepted_runs") != 24:
        errors.append("accepted run count is not 24")
    if acceptance.get("all_runtime_gates_pass") is not True:
        errors.append("top-level runtime acceptance gates did not pass")
    for key, label, start_event, end_event in WG2_INTERNAL_PHASES:
        item = by_key.get(key)
        if not item:
            errors.append(f"missing {key}")
            continue
        if not item.get("all_runtime_gates_pass", False):
            errors.append(f"{key} did not pass all runtime gates")
        if item.get("sample_count") != 300:
            errors.append(f"{key} does not contain 300 accepted samples")
        try:
            median = float(item["median_us"])
            p25 = float(item.get("p25_us", median))
            p75 = float(item.get("p75_us", median))
        except (KeyError, TypeError, ValueError):
            errors.append(f"{key} has invalid duration statistics")
            continue
        phases.append(
            {
                "key": key,
                "label": label,
                "start_event": start_event,
                "end_event": end_event,
                "median_us": median,
                "p25_us": p25,
                "p75_us": p75,
                "max_positive_overhead_pct": item.get(
                    "max_positive_overhead_pct"
                ),
                "sample_count": item.get("sample_count"),
                "all_runtime_gates_pass": bool(
                    item.get("all_runtime_gates_pass", False)
                ),
            }
        )
    accepted = not errors and len(phases) == len(WG2_INTERNAL_PHASES)
    return {
        "status": "accepted" if accepted else "rejected_or_incomplete",
        "source": public_source_ref(path),
        "source_sha256": sha256(path),
        "measurement_design": source.get("measurement_design"),
        "selected_partition": source.get("selected_partition"),
        "selected_ordinal": source.get("selected_ordinal"),
        "cohort": source.get("cohort"),
        "expected_samples_per_repeat": source.get(
            "expected_samples_per_repeat"
        ),
        "repeats_per_phase": source.get("repeats_per_phase"),
        "timing_protocol": source.get("timing_protocol"),
        "acceptance": source.get("acceptance"),
        "phases": phases if accepted else [],
        "reason": (
            "All eight selected steady-tile sparse pair probes passed and are shown as a statistical duration chain for one representative producer beat."
            if accepted
            else "; ".join(errors)
        ),
        "rejected_generation_note": source.get("rejected_generation_note"),
    }


def _normalize_direct_distribution(
    item: dict[str, Any], label: str, errors: list[str]
) -> dict[str, Any]:
    try:
        result = {
            "median_us": float(item["median_us"]),
            "q1_us": float(item["q1_us"]),
            "q3_us": float(item["q3_us"]),
            "iqr_us": float(item["iqr_us"]),
            "p90_us": float(item["p90_us"]),
            "p99_us": float(item["p99_us"]),
            "min_us": float(item["min_us"]),
            "max_us": float(item["max_us"]),
            "mean_us": float(item["mean_us"]),
        }
    except (KeyError, TypeError, ValueError):
        errors.append(f"{label} has invalid distribution statistics")
        return {}
    if not all(math.isfinite(value) for value in result.values()):
        errors.append(f"{label} contains non-finite statistics")
    if not (
        result["min_us"]
        <= result["q1_us"]
        <= result["median_us"]
        <= result["q3_us"]
        <= result["p90_us"]
        <= result["p99_us"]
        <= result["max_us"]
    ):
        errors.append(f"{label} quantiles are not ordered")
    if not math.isclose(
        result["iqr_us"], result["q3_us"] - result["q1_us"], abs_tol=1e-9
    ):
        errors.append(f"{label} IQR is inconsistent")
    return result


def normalize_wg2_full_axis(
    path: Path, source: dict[str, Any]
) -> dict[str, Any]:
    """Admit only the one-binary, same-launch generation-9 full axis."""
    errors: list[str] = []
    if source.get("analysis_status") != "accepted":
        errors.append("top-level analysis_status is not accepted")
    protocol = source.get("protocol") or {}
    expected_protocol = {
        "binary": "wg2_full_axis",
        "probe_id": 40,
        "event_ids": WG2_FULL_AXIS_EVENT_IDS,
        "origin_event_id": 0,
        "selected_partition": 1,
        "selected_ordinal": 14,
        "partition_tile_count": 24,
        "warpgroup": 2,
        "observer_lane": 0,
        "repeats": 3,
        "samples_per_run": 100,
        "name": "warmed_symbol_blocks_v1",
        "block_warmups": 30,
        "repeat_orders": ["control-first", "trace-first", "control-first"],
        "axis_kind": "same_launch_full_axis",
    }
    for key, expected in expected_protocol.items():
        if protocol.get(key) != expected:
            errors.append(f"protocol.{key} is not {expected!r}")
    deferred = protocol.get("deferred_flush_semantics")
    if not isinstance(deferred, str) or not deferred.strip():
        errors.append("protocol.deferred_flush_semantics is missing")

    acceptance = source.get("acceptance") or {}
    expected_acceptance = {
        "expected_runs": 3,
        "accepted_runs": 3,
        "expected_samples": 300,
        "accepted_samples": 300,
        "overhead_gate_pct": 5.0,
        "all_runs_runtime_protocol_match": True,
        "all_runs_bitwise_correct": True,
        "all_runs_exact_target_coverage": True,
        "all_runs_event_order_monotonic": True,
        "all_runs_zero_overflow": True,
        "all_runs_overhead_gates_pass": True,
        "all_runtime_gates_pass": True,
    }
    for key, expected in expected_acceptance.items():
        if acceptance.get(key) != expected:
            errors.append(f"acceptance.{key} is not {expected!r}")
    for key in ("maximum_median_overhead_pct", "maximum_p90_overhead_pct"):
        try:
            if float(acceptance[key]) > 5.0:
                errors.append(f"acceptance.{key} exceeds 5%")
        except (KeyError, TypeError, ValueError):
            errors.append(f"acceptance.{key} is invalid")

    raw_landmarks = source.get("landmarks") or []
    if [item.get("event_id") for item in raw_landmarks] != WG2_FULL_AXIS_EVENT_IDS:
        errors.append("landmark event IDs are not canonical and ordered")
    landmarks: list[dict[str, Any]] = []
    for item in raw_landmarks:
        event_id = item.get("event_id")
        distribution = _normalize_direct_distribution(
            item, f"landmark E{event_id}", errors
        )
        if item.get("n_runs") != 3 or item.get("n_samples") != 300:
            errors.append(f"landmark E{event_id} is not 3 runs / 300 samples")
        if item.get("all_runtime_gates_pass") is not True:
            errors.append(f"landmark E{event_id} did not pass runtime gates")
        run_medians = item.get("run_medians_us") or []
        if len(run_medians) != 3 or not all(
            isinstance(value, (int, float)) and math.isfinite(value)
            for value in run_medians
        ):
            errors.append(f"landmark E{event_id} lacks three run medians")
        landmarks.append(
            {
                "event_id": event_id,
                "label": item.get("label"),
                "n_runs": item.get("n_runs"),
                "n_samples": item.get("n_samples"),
                **distribution,
                "run_medians_us": run_medians,
                "all_runtime_gates_pass": bool(
                    item.get("all_runtime_gates_pass")
                ),
            }
        )
    if any(
        right.get("median_us", math.inf) < left.get("median_us", -math.inf)
        for left, right in zip(landmarks, landmarks[1:])
    ):
        errors.append("same-launch landmark medians are not monotonic")

    raw_segments = source.get("segments") or []
    expected_segments = [
        (key, label, int(start), int(end))
        for key, label, start, end in WG2_INTERNAL_PHASES
    ]
    if len(raw_segments) != 8:
        errors.append("direct segment count is not eight")
    phases: list[dict[str, Any]] = []
    for index, (key, label, start_id, end_id) in enumerate(expected_segments):
        item = raw_segments[index] if index < len(raw_segments) else {}
        if item.get("key") != key:
            errors.append(f"segment {index} key is not {key}")
        if item.get("start_event_id") != start_id or item.get("end_event_id") != end_id:
            errors.append(f"segment {key} event edge is wrong")
        if item.get("measurement_semantics") != "direct_same_launch_difference":
            errors.append(f"segment {key} is not a direct same-launch difference")
        if item.get("n_runs") != 3 or item.get("n_samples") != 300:
            errors.append(f"segment {key} is not 3 runs / 300 samples")
        if item.get("all_runtime_gates_pass") is not True:
            errors.append(f"segment {key} did not pass runtime gates")
        distribution = _normalize_direct_distribution(item, f"segment {key}", errors)
        run_medians = item.get("run_medians_us") or []
        if len(run_medians) != 3:
            errors.append(f"segment {key} lacks three run medians")
        phases.append(
            {
                "key": key,
                "label": label,
                "start_event": str(start_id),
                "end_event": str(end_id),
                "measurement_semantics": "direct_same_launch_difference",
                "sample_count": item.get("n_samples"),
                "median_us": distribution.get("median_us"),
                "p25_us": distribution.get("q1_us"),
                "p75_us": distribution.get("q3_us"),
                **distribution,
                "run_medians_us": run_medians,
                "all_runtime_gates_pass": bool(
                    item.get("all_runtime_gates_pass")
                ),
            }
        )

    raw_total = source.get("total") or {}
    if (
        raw_total.get("start_event_id") != 0
        or raw_total.get("end_event_id") != 13
        or raw_total.get("measurement_semantics")
        != "direct_same_launch_difference"
        or raw_total.get("n_runs") != 3
        or raw_total.get("n_samples") != 300
        or raw_total.get("all_runtime_gates_pass") is not True
    ):
        errors.append("direct total contract is invalid")
    total = {
        **_normalize_direct_distribution(raw_total, "direct total", errors),
        "n_runs": raw_total.get("n_runs"),
        "n_samples": raw_total.get("n_samples"),
        "run_medians_us": raw_total.get("run_medians_us", []),
    }

    closure = source.get("closure") or {}
    expected_closure = {
        "method": "per_launch_integer_nanosecond_telescoping",
        "residual_count": 300,
        "max_abs_residual_ns": 0,
        "all_residuals_zero": True,
        "passes": True,
    }
    for key, expected in expected_closure.items():
        if closure.get(key) != expected:
            errors.append(f"closure.{key} is not {expected!r}")

    rejected = source.get("rejected_gen8") or {}
    if (
        rejected.get("analysis_status") != "rejected"
        or rejected.get("reason")
        != "non_monotonic_independent_binary_endpoint_medians"
        or rejected.get("used_for_phase_attribution") is not False
        or rejected.get("rescaled") is not False
    ):
        errors.append("generation-8 rejection is missing or altered")
    try:
        if not float(rejected["event9_median_us"]) < float(
            rejected["event8_median_us"]
        ):
            errors.append("generation-8 rejection lacks E8→E9 reversal")
    except (KeyError, TypeError, ValueError):
        errors.append("generation-8 rejection medians are invalid")

    resources = source.get("resources") or {}
    if resources.get("status") != "accepted" or resources.get("accepted") is not True:
        errors.append("generation-9 resource evidence is not accepted")

    representative = source.get("representative_axis") or {}
    if not representative:
        errors.append("representative real same-launch axis is missing")
    else:
        if representative.get("event_ids") != WG2_FULL_AXIS_EVENT_IDS:
            errors.append("representative axis event IDs are wrong")
        cumulative = representative.get("cumulative_us_by_event") or {}
        adjacent = representative.get("adjacent_delta_us_by_edge") or {}
        if [int(key) for key in cumulative] != WG2_FULL_AXIS_EVENT_IDS:
            errors.append("representative cumulative landmark map is wrong")
        expected_edges = [f"{start}_{end}" for _, _, start, end in expected_segments]
        if list(adjacent) != expected_edges:
            errors.append("representative adjacent edge map is wrong")
        try:
            cumulative_values = [float(cumulative[str(event)]) for event in WG2_FULL_AXIS_EVENT_IDS]
            adjacent_values = [float(adjacent[edge]) for edge in expected_edges]
            if cumulative_values[0] != 0 or any(
                right < left for left, right in zip(cumulative_values, cumulative_values[1:])
            ):
                errors.append("representative cumulative axis is not monotonic")
            if any(value < 0 for value in adjacent_values):
                errors.append("representative adjacent axis contains negative durations")
            if not math.isclose(sum(adjacent_values), cumulative_values[-1], abs_tol=1e-9):
                errors.append("representative axis does not telescope")
            if not math.isclose(float(representative["total_us"]), cumulative_values[-1], abs_tol=1e-9):
                errors.append("representative total is inconsistent")
            if representative.get("closure_residual_ns") != 0:
                errors.append("representative closure residual is nonzero")
        except (KeyError, TypeError, ValueError):
            errors.append("representative axis values are invalid")

    accepted = not errors and len(landmarks) == 9 and len(phases) == 8
    return {
        "status": "accepted" if accepted else "rejected_or_incomplete",
        "measurement_mode": "same_launch_full_axis",
        "source": public_source_ref(path),
        "source_sha256": sha256(path),
        "protocol": protocol,
        "acceptance": acceptance,
        "selected_partition": protocol.get("selected_partition"),
        "selected_ordinal": protocol.get("selected_ordinal"),
        "partition_tile_count": protocol.get("partition_tile_count"),
        "landmarks": landmarks if accepted else [],
        "phases": phases if accepted else [],
        "total": total if accepted else {},
        "closure": closure if accepted else {},
        "representative_axis": representative if accepted else {},
        "rejected_gen8": rejected,
        "resources": resources,
        "provenance": source.get("provenance", {}),
        "reason": (
            "All nine landmarks and eight adjacent phases are direct same-launch measurements from one binary; the drawn axis is one real accepted sample."
            if accepted
            else "; ".join(errors)
        ),
    }


def normalize_wg2_cumulative_axis(
    path: Path, source: dict[str, Any]
) -> dict[str, Any]:
    """Admit only the final eight-endpoint generation-8 cumulative axis.

    Every endpoint is a direct event-0-to-event-E duration distribution from
    its own accepted binary.  Adjacent phase widths are therefore differences
    of endpoint medians across binaries, not within-launch phase durations.
    """
    errors: list[str] = []
    if source.get("analysis_status") != "accepted":
        errors.append("top-level analysis_status is not accepted")
    if source.get("measurement_design") != "gen8_cumulative_endpoint_axis":
        errors.append("measurement design is not generation-8 cumulative axis")
    protocol = source.get("protocol") or {}
    expected_protocol = {
        "selected_partition": 1,
        "selected_ordinal": 14,
        "partition_tile_count": 24,
        "origin_event_id": 0,
        "repeats_per_endpoint": 3,
        "samples_per_run": 100,
        "name": "warmed_symbol_blocks_v1",
        "block_warmups": 30,
        "repeat_orders": [
            "control-first",
            "trace-first",
            "control-first",
        ],
        "endpoint_pooling": "pooled_3x100_samples",
        "quantile_method": "linear_interpolation_on_sorted_samples",
        "trace_sample_capture": (
            "one preallocated buffer per timed launch; bulk D2H collection after the trace block"
        ),
    }
    for key, expected in expected_protocol.items():
        if protocol.get(key) != expected:
            errors.append(f"protocol.{key} is not {expected!r}")

    acceptance = source.get("acceptance") or {}
    if acceptance.get("expected_endpoints") != 8:
        errors.append("acceptance.expected_endpoints is not 8")
    if acceptance.get("accepted_endpoints") != 8:
        errors.append("acceptance.accepted_endpoints is not 8")
    if acceptance.get("expected_endpoint_runs") != 24:
        errors.append("acceptance.expected_endpoint_runs is not 24")
    if acceptance.get("accepted_endpoint_runs") != 24:
        errors.append("acceptance.accepted_endpoint_runs is not 24")
    if acceptance.get("accepted_samples") != 2400:
        errors.append("acceptance.accepted_samples is not 2400")
    if acceptance.get("expected_samples_per_run") != 100:
        errors.append("acceptance.expected_samples_per_run is not 100")
    if acceptance.get("overhead_gate_pct") != 5.0:
        errors.append("acceptance.overhead_gate_pct is not 5")
    for key in ("maximum_median_overhead_pct", "maximum_p90_overhead_pct"):
        try:
            if float(acceptance[key]) > 5.0:
                errors.append(f"acceptance.{key} exceeds 5%")
        except (KeyError, TypeError, ValueError):
            errors.append(f"acceptance.{key} is invalid")
    for key in (
        "all_runs_bitwise_correct",
        "all_runs_exact_target_coverage",
        "all_runs_zero_overflow",
        "all_runtime_gates_pass",
    ):
        if acceptance.get(key) is not True:
            errors.append(f"acceptance.{key} is not true")

    axis_semantics = source.get("axis_semantics") or {}
    expected_axis_semantics = {
        "reference_event_id": 0,
        "endpoint_event_ids": WG2_CUMULATIVE_ENDPOINT_IDS,
        "sample_semantics": "same-launch same-lane cumulative t(E)-t(0)",
        "adjacent_gap_semantics": (
            "independent-axis statistical difference, not same-launch phase samples"
        ),
    }
    for key, expected in expected_axis_semantics.items():
        if axis_semantics.get(key) != expected:
            errors.append(f"axis_semantics.{key} is not {expected!r}")

    raw_endpoints = source.get("endpoints") or []
    endpoint_ids = [item.get("event_id") for item in raw_endpoints]
    if endpoint_ids != WG2_CUMULATIVE_ENDPOINT_IDS:
        errors.append(
            "endpoint IDs are not the canonical ordered [2,3,4,5,7,8,9,13]"
        )
    endpoints: list[dict[str, Any]] = []
    for item in raw_endpoints:
        event_id = item.get("event_id")
        try:
            median = float(item["median_us"])
            q1 = float(item["q1_us"])
            q3 = float(item["q3_us"])
            p90 = float(item["p90_us"])
            minimum = float(item["min_us"])
            maximum = float(item["max_us"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"endpoint {event_id} has invalid statistics")
            continue
        if item.get("n_runs") != 3 or item.get("n_samples") != 300:
            errors.append(f"endpoint {event_id} is not 3 runs / 300 samples")
        if item.get("all_runtime_gates_pass") is not True:
            errors.append(f"endpoint {event_id} did not pass runtime gates")
        if not all(
            math.isfinite(value)
            for value in (median, q1, q3, p90, minimum, maximum)
        ):
            errors.append(f"endpoint {event_id} contains non-finite statistics")
        if not minimum <= q1 <= median <= q3 <= p90 <= maximum:
            errors.append(f"endpoint {event_id} quantiles are not ordered")
        run_medians = item.get("run_medians_us") or []
        if len(run_medians) != 3 or not all(
            isinstance(value, (int, float)) and math.isfinite(value)
            for value in run_medians
        ):
            errors.append(f"endpoint {event_id} does not have three run medians")
        if not math.isclose(float(item.get("iqr_us", math.nan)), q3 - q1, abs_tol=1e-9):
            errors.append(f"endpoint {event_id} IQR is inconsistent")
        try:
            if float(item["max_positive_overhead_pct"]) > 5.0:
                errors.append(f"endpoint {event_id} exceeds 5% overhead")
        except (KeyError, TypeError, ValueError):
            errors.append(f"endpoint {event_id} overhead is invalid")
        endpoints.append(
            {
                "event_id": event_id,
                "label": item.get("label"),
                "n_runs": item.get("n_runs"),
                "n_samples": item.get("n_samples"),
                "median_us": median,
                "q1_us": q1,
                "q3_us": q3,
                "iqr_us": item.get("iqr_us"),
                "p90_us": p90,
                "min_us": minimum,
                "max_us": maximum,
                "run_medians_us": run_medians,
                "max_positive_overhead_pct": item.get(
                    "max_positive_overhead_pct"
                ),
                "repeats": item.get("repeats", []),
                "all_runtime_gates_pass": bool(
                    item.get("all_runtime_gates_pass")
                ),
            }
        )
    if any(
        right["median_us"] < left["median_us"]
        for left, right in zip(endpoints, endpoints[1:])
    ):
        errors.append("cumulative endpoint medians are not monotonic")

    endpoint_by_id = {item["event_id"]: item for item in endpoints}
    expected_pairs = [
        (key, label, int(start), int(end))
        for key, label, start, end in WG2_INTERNAL_PHASES
    ]
    raw_segments = source.get("adjacent_segments") or []
    if len(raw_segments) != len(expected_pairs):
        errors.append("adjacent segment count is not eight")
    phases: list[dict[str, Any]] = []
    previous_median = 0.0
    for index, (key, label, start_id, end_id) in enumerate(expected_pairs):
        item = raw_segments[index] if index < len(raw_segments) else {}
        if item.get("key") != key:
            errors.append(f"adjacent segment {index} key is not {key}")
        if item.get("start_event_id") != start_id:
            errors.append(f"{key} start event is not {start_id}")
        if item.get("end_event_id") != end_id:
            errors.append(f"{key} end event is not {end_id}")
        if (
            item.get("derivation")
            != "difference_of_independent_endpoint_pooled_medians"
        ):
            errors.append(f"{key} does not declare the cross-binary derivation")
        if item.get("has_direct_segment_distribution") is not False:
            errors.append(f"{key} incorrectly claims a direct distribution")
        endpoint = endpoint_by_id.get(end_id)
        if endpoint is None:
            continue
        expected_difference = endpoint["median_us"] - previous_median
        try:
            reported_difference = float(
                item["derived_median_difference_us"]
            )
        except (KeyError, TypeError, ValueError):
            errors.append(f"{key} has no valid derived median difference")
            reported_difference = expected_difference
        if not math.isclose(
            reported_difference, expected_difference, abs_tol=1e-9
        ):
            errors.append(f"{key} does not equal its endpoint-median difference")
        if reported_difference < 0:
            errors.append(f"{key} has a negative derived duration")
        try:
            if not math.isclose(
                float(item["start_endpoint_median_us"]),
                previous_median,
                abs_tol=1e-9,
            ) or not math.isclose(
                float(item["end_endpoint_median_us"]),
                endpoint["median_us"],
                abs_tol=1e-9,
            ):
                errors.append(f"{key} endpoint medians are inconsistent")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{key} endpoint median fields are invalid")
        phases.append(
            {
                "key": key,
                "label": label,
                "start_event": str(start_id),
                "end_event": str(end_id),
                "start_median_us": previous_median,
                "end_median_us": endpoint["median_us"],
                "median_us": reported_difference,
                "duration_kind": "cross_binary_endpoint_median_difference",
                "sample_count_per_endpoint": endpoint["n_samples"],
            }
        )
        previous_median = endpoint["median_us"]

    closure = source.get("closure") or {}
    if (
        closure.get("method")
        != "telescoping_adjacent_differences_of_endpoint_medians"
    ):
        errors.append("closure method is not the accepted telescoping method")
    if closure.get("passes") is not True:
        errors.append("closure does not pass")
    if closure.get("is_measurement_independence_claim") is not False:
        errors.append("closure incorrectly claims measurement independence")
    try:
        endpoint_13 = float(closure["event0_to_13_median_us"])
        segment_sum = float(
            closure["sum_adjacent_median_differences_us"]
        )
        residual = float(closure["residual_us"])
    except (KeyError, TypeError, ValueError):
        errors.append("closure statistics are invalid")
        endpoint_13 = previous_median
        segment_sum = sum(item["median_us"] for item in phases)
        residual = endpoint_13 - segment_sum
    if endpoints and not math.isclose(
        endpoint_13, endpoints[-1]["median_us"], abs_tol=1e-9
    ):
        errors.append("closure endpoint does not match event 13 median")
    if not math.isclose(
        segment_sum,
        sum(item["median_us"] for item in phases),
        abs_tol=1e-9,
    ):
        errors.append("closure segment sum does not match adjacent differences")
    if not math.isclose(residual, segment_sum - endpoint_13, abs_tol=1e-9):
        errors.append("closure residual is inconsistent")

    crosschecks = []
    raw_crosschecks = source.get("optional_gen7_crosschecks", [])
    expected_crosschecks = {
        "tile_to_r0_index": (0, 2),
        "k_buffer_wait": (2, 3),
        "r1_rope": (8, 9),
        "publish": (9, 13),
    }
    if len(raw_crosschecks) not in (0, len(expected_crosschecks)):
        errors.append("generation-7 cross-check set is partial")
    if raw_crosschecks and [item.get("key") for item in raw_crosschecks] != list(
        expected_crosschecks
    ):
        errors.append("generation-7 cross-check keys are not canonical")
    for item in raw_crosschecks:
        if item.get("status") != "accepted":
            errors.append("a generation-7 cross-check is not accepted")
            continue
        try:
            key = item["key"]
            expected_start, expected_end = expected_crosschecks[key]
            if (
                int(item["start_event_id"]) != expected_start
                or int(item["end_event_id"]) != expected_end
            ):
                errors.append(f"generation-7 cross-check {key} has wrong events")
            if int(item["n_samples"]) != 300:
                errors.append(f"generation-7 cross-check {key} is not n=300")
            normalized_crosscheck = {
                "key": key,
                "start_event_id": int(item["start_event_id"]),
                "end_event_id": int(item["end_event_id"]),
                "status": "accepted",
                "median_us": float(item["median_us"]),
                "q1_us": float(item["q1_us"]),
                "q3_us": float(item["q3_us"]),
                "n_samples": int(item["n_samples"]),
                "max_positive_overhead_pct": float(
                    item["max_positive_overhead_pct"]
                ),
            }
            if not (
                normalized_crosscheck["q1_us"]
                <= normalized_crosscheck["median_us"]
                <= normalized_crosscheck["q3_us"]
            ):
                errors.append(f"generation-7 cross-check {key} quantiles are not ordered")
            if normalized_crosscheck["max_positive_overhead_pct"] > 5.0:
                errors.append(f"generation-7 cross-check {key} exceeds 5% overhead")
            crosschecks.append(normalized_crosscheck)
        except (KeyError, TypeError, ValueError):
            errors.append("an accepted generation-7 cross-check is malformed")

    accepted = not errors and len(endpoints) == 8 and len(phases) == 8
    return {
        "status": "accepted" if accepted else "rejected_or_incomplete",
        "measurement_mode": "cumulative_axis",
        "source": public_source_ref(path),
        "source_sha256": sha256(path),
        "protocol": protocol,
        "axis_semantics": axis_semantics,
        "acceptance": acceptance,
        "provenance": source.get("provenance", {}),
        "resources": source.get("resources", {}),
        "selected_partition": protocol.get("selected_partition"),
        "selected_ordinal": protocol.get("selected_ordinal"),
        "partition_tile_count": protocol.get("partition_tile_count"),
        "expected_samples_per_repeat": protocol.get("samples_per_run"),
        "repeats_per_phase": protocol.get("repeats_per_endpoint"),
        "endpoints": endpoints if accepted else [],
        "phases": phases if accepted else [],
        "closure": {
            "method": closure.get("method"),
            "event0_to_13_median_us": endpoint_13,
            "sum_adjacent_median_differences_us": segment_sum,
            "residual_us": residual,
        }
        if accepted
        else {},
        "optional_gen7_crosschecks": crosschecks if accepted else [],
        "reason": (
            "Eight accepted event-0 cumulative endpoints define a common statistical axis; adjacent widths are cross-binary differences of endpoint medians."
            if accepted
            else "; ".join(errors)
        ),
    }


def build_wg2_phase_analysis_from_runs(
    runs_root: Path, expected_samples_per_repeat: int = 100
) -> dict[str, Any]:
    """Build the optional compact eight-phase file from accepted sparse-pair runs.

    The accepted microscope samples one non-straggler CTA at steady ordinal 14
    on every traced iteration, so each pair contributes 100 direct within-launch
    durations per repeat without paying an all-CTA or all-tile trace cost.
    All eight variants and all three fresh-process repeats must pass every
    correctness, coverage, overflow, and overhead gate before this function
    returns a renderable payload.
    """
    pair_names = {
        "tile_to_r0_index": "wg2_deferred_pair_0_2",
        "k_buffer_wait": "wg2_deferred_pair_2_3",
        "r0_nope": "wg2_deferred_pair_3_4",
        "r0_rope": "wg2_deferred_pair_4_5",
        "r1_index": "wg2_deferred_pair_5_7",
        "r1_nope": "wg2_deferred_pair_7_8",
        "r1_rope": "wg2_deferred_pair_8_9",
        "publish": "wg2_deferred_pair_9_13",
    }
    phase_lookup = {key: (label, start, end) for key, label, start, end in WG2_INTERNAL_PHASES}
    if expected_samples_per_repeat <= 0:
        raise ValueError("expected_samples_per_repeat must be positive")
    result = {
        "schema_version": "flashmla-wg2-repeated-single-cta-phase-analysis/v3",
        "measurement_design": "repeated_single_cta_microscope",
        "selected_partition": 1,
        "selected_ordinal": 14,
        "cohort": "partition 1 (non-straggler 24-tile CTA), ordinal 14, repeated traced iterations",
        "expected_samples_per_repeat": expected_samples_per_repeat,
        "phases": [],
    }
    for key, variant in pair_names.items():
        label, start_event_id, end_event_id = phase_lookup[key]
        start_event_id = int(start_event_id)
        end_event_id = int(end_event_id)
        values = []
        overheads = []
        repeat_sources = []
        for repeat in range(1, 4):
            run = runs_root / f"{variant}-r{repeat}"
            summary_path = run / "summary.json"
            trace_path = run / "trace_events.csv"
            iteration_path = run / "iteration_pair_deltas.csv"
            if (
                not summary_path.exists()
                or not trace_path.exists()
                or not iteration_path.exists()
            ):
                raise ValueError(f"missing selected steady-tile run artifacts: {run}")
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            correctness = summary.get("trace_correctness", {})
            reference = summary.get("correctness_vs_reference", {})
            coverage = summary.get("trace_coverage", {})
            selected = coverage.get("selected_ordinal_contract") or {}
            iteration_contract = (
                coverage.get("selected_iteration_contract") or {}
            )
            gates = [
                summary.get("overhead_gate_pass") is True,
                correctness
                and all(value is True for value in correctness.values()),
                reference.get("out_bitwise_equal") is True,
                reference.get("lse_bitwise_equal") is True,
                coverage.get("overflow_sum") == 0,
                coverage.get("unexpected_tile_event_records") == [],
                selected.get("pass") is True,
                selected.get("selected_ordinal") == 14,
                selected.get("expected_cohort_ctas") == 1,
                selected.get("recorded_selected_tiles") == 1,
                selected.get("expected_partition_ids") == [1],
                selected.get("recorded_selected_partitions") == [1],
                (selected.get("pair_interval_us") or {}).get("count") == 1,
                iteration_contract.get("pass") is True,
                iteration_contract.get("selected_partition") == 1,
                iteration_contract.get("selected_ordinal") == 14,
                iteration_contract.get("expected_iterations")
                == expected_samples_per_repeat,
                iteration_contract.get("recorded_iterations")
                == expected_samples_per_repeat,
                iteration_contract.get("event_ids")
                == [start_event_id, end_event_id],
                iteration_contract.get("missing_iterations") == [],
                iteration_contract.get("duplicate_iterations") == [],
                iteration_contract.get("unexpected_record_locations") == [],
                iteration_contract.get("overflow_sum") == 0,
                (iteration_contract.get("pair_delta_summary_us") or {}).get(
                    "count"
                )
                == expected_samples_per_repeat,
            ]
            if not all(gates):
                raise ValueError(
                    f"{run}: failed selected steady-tile acceptance gate vector {gates}"
                )
            repeat_values = [
                float(value)
                for value in iteration_contract.get("pair_deltas_us", [])
            ]
            with iteration_path.open(newline="", encoding="utf-8") as handle:
                iteration_csv_values = [
                    float(row["delta_us"]) for row in csv.DictReader(handle)
                ]
            if iteration_csv_values != repeat_values:
                raise ValueError(
                    f"{iteration_path}: values differ from summary contract"
                )
            if len(repeat_values) != expected_samples_per_repeat:
                raise ValueError(
                    f"{summary_path}: expected {expected_samples_per_repeat} "
                    f"iteration phase deltas, got {len(repeat_values)}"
                )
            if not all(
                math.isfinite(value) and value >= 0 for value in repeat_values
            ):
                raise ValueError(f"{summary_path}: invalid iteration phase delta")
            values.extend(repeat_values)
            overheads.extend(
                [
                    float(summary["trace_overhead_median_pct"]),
                    float(summary["trace_overhead_p90_pct"]),
                ]
            )
            repeat_sources.append(
                {
                    "repeat": repeat,
                    "summary": public_source_ref(summary_path),
                    "summary_sha256": sha256(summary_path),
                    "trace": public_source_ref(trace_path),
                    "trace_sha256": sha256(trace_path),
                    "iteration_pair_deltas": public_source_ref(
                        iteration_path
                    ),
                    "iteration_pair_deltas_sha256": sha256(iteration_path),
                    "duration_us": summarize(repeat_values),
                    "overhead_median_pct": summary[
                        "trace_overhead_median_pct"
                    ],
                    "overhead_p90_pct": summary["trace_overhead_p90_pct"],
                }
            )
        phase_stats = summarize(values)
        result["phases"].append(
            {
                "key": key,
                "label": label,
                "variant": variant,
                "sampled_ordinal": 14,
                "sample_count": len(values),
                "median_us": phase_stats["p50_us"],
                "p25_us": percentile(values, 0.25),
                "p75_us": percentile(values, 0.75),
                "p90_us": phase_stats["p90_us"],
                "min_us": phase_stats["min_us"],
                "max_us": phase_stats["max_us"],
                "max_positive_overhead_pct": max(0.0, max(overheads)),
                "all_runtime_gates_pass": True,
                "repeats": repeat_sources,
            }
        )
    return result


def build_exact_five_piece(scaffold: dict[str, Any]) -> list[dict[str, Any]]:
    selected = scaffold["selected_critical_cta"]
    accounting = selected["observed_region_accounting"]
    pieces = [
        {
            "key": "launch_skew",
            "label": "Launch skew",
            "detail": "first CTA enter → partition 65 enter",
            "duration_us": selected["start_us_from_launch"],
            "kind": "launch",
        },
        {
            "key": "producer_prologue",
            "label": "Producer prologue",
            "detail": "CTA enter → first WG2 tile",
            "duration_us": accounting["before_first_wg2_us"],
            "kind": "setup",
        },
        {
            "key": "wg2_windows",
            "label": "29 producer windows",
            "detail": "union of TILE_BEGIN → K-ready intervals",
            "duration_us": accounting["wg2_service_union_us"],
            "kind": "service",
        },
        {
            "key": "intertile_gaps",
            "label": "Inter-tile gaps",
            "detail": "28 gaps between producer windows",
            "duration_us": accounting["between_wg2_windows_us"],
            "kind": "gap",
        },
        {
            "key": "final_drain",
            "label": "Final drain",
            "detail": "last K-ready → critical CTA exit",
            "duration_us": accounting["after_last_wg2_us"],
            "kind": "drain",
        },
    ]
    total = sum(item["duration_us"] for item in pieces)
    if abs(total - scaffold["makespan_us"]) > 1e-9:
        raise ValueError(
            f"five-piece scaffold does not close: {total} vs {scaffold['makespan_us']}"
        )
    return pieces


def build_payload(
    manifest_path: Path, optional_wg2_analysis_override: Path | None = None
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_dir = manifest_path.parent
    scaffold_path = (manifest_dir / manifest["accepted_scaffold"]["path"]).resolve()
    detail_path = (manifest_dir / manifest["perturbed_reference"]["path"]).resolve()
    scaffold_rows = load_rows(scaffold_path)
    detail_rows = load_rows(detail_path)
    scaffold = scaffold_analysis(scaffold_rows, manifest)
    detail = detailed_reference_analysis(detail_rows, manifest)
    accepted_analysis_path = (
        manifest_dir / manifest["accepted_probe_analysis"]["path"]
    ).resolve()
    accepted_analysis = load_accepted_probe_analysis(accepted_analysis_path)
    optional_wg2_path = optional_wg2_analysis_override or (
        manifest_dir / manifest["optional_wg2_internal_analysis"]["path"]
    ).resolve()
    optional_wg2_internal = normalize_optional_wg2_internal(optional_wg2_path)
    rejected_gen9_path = (
        manifest_dir / manifest["rejected_gen9_mechanistic_shape"]["path"]
    ).resolve()
    rejected_gen9_shape = load_rejected_gen9_mechanistic_shape(rejected_gen9_path)
    rejected_gen13_path = (
        manifest_dir / manifest["rejected_gen13_stop_record"]["path"]
    ).resolve()
    rejected_gen13 = load_gen13_stop_record(rejected_gen13_path)
    microscope_outer_reference = load_wg2_microscope_outer_reference(
        manifest_dir, manifest["wg2_microscope_outer_reference"]
    )
    probes = [
        analyze_sparse_probe(
            spec,
            manifest_dir,
            scaffold_rows,
            scaffold,
            manifest["alignment_policy"],
        )
        for spec in manifest["sparse_probe_sets"]
    ]

    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    duration_us = scaffold["makespan_us"]
    return {
        "artifact": {
            "name": manifest["title"],
            "generated_at": generated_at,
            "sources": [
                public_source_ref(manifest_path),
                public_source_ref(scaffold_path),
                public_source_ref(detail_path),
                public_source_ref(accepted_analysis_path),
                public_source_ref(rejected_gen9_path),
                public_source_ref(rejected_gen13_path),
                *(
                    [public_source_ref(optional_wg2_path)]
                    if optional_wg2_path.exists()
                    else []
                ),
            ],
            "time_base_note": "t=0 is the first CTA_ENTER in the exact accepted scaffold run. The partition-65 consumer lanes are three-repeat median CTA-relative landmarks from separate accepted launches, translated to that CTA start and labeled as a statistical composite.",
        },
        "bin_seconds": duration_us / 1_000_000,
        "duration_seconds": duration_us / 1_000_000,
        "profile_start_note": "Exact accepted scaffold: first CTA_ENTER to last CTA_EXIT.",
        "category_colors": {"flashmla_scaffold": "#176b87"},
        "category_totals": {
            "flashmla_scaffold": {
                "count": 1,
                "total_ms": duration_us / 1000,
                "top_kernel_names": ["flash_fwd_splitkv_mla_fp8_sparse_kernel"],
                "interpretation": "Accepted low-overhead source CTA-grid envelope; not CUDA API duration.",
            }
        },
        "bins": [
            {
                "t": 0,
                "kernel_ms": {"flashmla_scaffold": duration_us / 1000},
                "kernel_count": {"flashmla_scaffold": 1},
                "decode_graph_ms": 0,
                "decode_graph_count": 0,
            }
        ],
        "flashmla_composite": {
            "schema_version": "flashmla-composite-timeline/v1",
            "status": (
                "accepted_absolute_scaffold_and_consumers_with_wg2_internal_split"
                if optional_wg2_internal["status"] == "accepted"
                else "accepted_absolute_timeline_internal_wg2_unresolved_by_low_overhead_probes"
            ),
            "workload_identity": manifest["workload_identity"],
            "production_anchor": manifest["production_anchor"],
            "accepted_scaffold": scaffold,
            "exact_five_piece_scaffold": build_exact_five_piece(scaffold),
            "accepted_probe_analysis": accepted_analysis,
            "optional_wg2_internal": optional_wg2_internal,
            "rejected_gen9_mechanistic_shape": rejected_gen9_shape,
            "rejected_gen13_stop_record": rejected_gen13,
            "wg2_microscope_outer_reference": microscope_outer_reference,
            "rejected_wg2_internal_generation": manifest[
                "rejected_wg2_internal_generation"
            ],
            "rejected_wg2_all_cta_selected_ordinal_generation": manifest[
                "rejected_wg2_all_cta_selected_ordinal_generation"
            ],
            "rejected_wg2_selected_cohort_generation": manifest[
                "rejected_wg2_selected_cohort_generation"
            ],
            "absolute_lanes": {
                "CTA": {
                    "status": "measured",
                    "coverage": "enter/exit for all 132 CTAs",
                },
                "WG2": {
                    "status": "measured_partial",
                    "coverage": "TILE_BEGIN through K_READY publication for all 3,200 producer tiles",
                },
                "WG0": {
                    "status": "accepted_statistical_composite",
                    "coverage": "Nine source landmarks across 29 ordinals, three accepted repeats",
                },
                "WG1": {
                    "status": "accepted_statistical_composite",
                    "coverage": "Six source landmarks across 29 ordinals, three accepted repeats",
                },
            },
            "perturbed_reference": detail,
            "alignment_policy": manifest["alignment_policy"],
            "sparse_probe_sets": probes,
            "interpretation_contract": {
                "proven_absolute": "Production outer duration, exact CTA/WG2 scaffold, accepted CTA setup/drain landmarks, and accepted within-probe phase durations.",
                "proven_mechanism": "Detailed trace ordering and overlap on its own perturbed clock.",
                "statistical_composite": "WG0/WG1 absolute lanes are per-ordinal three-repeat medians translated across separate accepted launches; they are not one cycle-exact launch.",
                "wg2_full_axis": "When accepted, all nine WG2 landmarks and all eight adjacent phases come from the same binary, lane, tile, and launch, with timestamps flushed after the producer loop.",
                "rejected_gen8": "Independent cumulative endpoint medians were non-monotonic, so generation 8 contributes no accepted adjacent phase widths.",
                "rejected_gen9": "The one-binary nine-landmark trace preserved correct order and exact closure but imposed about 30% runtime overhead in all three repeats, so it contributes no phase widths.",
                "rejected_gen10": "The 1,800 MHz clock64 one-binary full axis preserved correct order and exact closure but imposed 31.305% median and 30.617% p90 overhead, so it contributes no phase widths.",
                "rejected_gen11": "Uniform all-CTA ordinal-14 E3-to-E4 capture passed its 125-CTA contract but imposed 15.325% median and 14.570% p90 overhead, so it contributes no phase width.",
                "rejected_gen12": "Uniform all-CTA/all-3,200-tile E3-to-E4 capture exactly matched the accepted topology but imposed about 15.7% overhead; hot-path internal stores therefore contribute no accepted phase width.",
                "rejected_gen13": f"Even two register-held clock32 values with no hot-interval memory stores imposed {rejected_gen13['median_overhead_pct']:.6f}% median and {rejected_gen13['p90_overhead_pct']:.6f}% p90 overhead, so the source-level experiment ladder stops without an accepted absolute internal split.",
                "measurement_limit": "The exact outer cadence and accepted consumer phases are measurable below the 5% gate. The eight-way WG2 interior is not: every tested source-level internal probe changed the hot path too much.",
                "forbidden_claim": "Do not sum overlapping lane residency or scale +73% detailed-trace microseconds onto the 103.200 us production duration.",
            },
            "experiment_ladder": [
                {"generation": "Accepted outer probes", "result": "39/39 accepted", "detail": "Exact 100.704 us scaffold, all 3,200 producer windows, CTA edges, WG0/WG1 phases, and relays passed the <=5% gate.", "accepted": True},
                {"generation": "Gen2–5", "result": "+5.36% to +17.89%", "detail": "Sparse pair, all-CTA ordinal, and 25-CTA cohort designs crossed the observer gate.", "accepted": False},
                {"generation": "Gen8", "result": "non-monotonic", "detail": "Independent cumulative endpoint medians reversed at E8→E9, so no adjacent width was admitted.", "accepted": False},
                {"generation": "Gen9", "result": "+29.61% to +30.67% median", "detail": "One same-launch nine-landmark axis closed exactly for all 300 samples, but strongly perturbed runtime. Retained only as the normalized mechanism inset.", "accepted": False},
                {"generation": "Gen10", "result": "+31.305% median", "detail": "clock64 full-axis capture falsified the hypothesis that globaltimer alone caused the overhead; selected-CTA pair variants also failed multiple edges.", "accepted": False},
                {"generation": "Gen11", "result": "+15.325% median", "detail": "All-CTA ordinal-14 E3→E4 pair passed coverage but failed timing.", "accepted": False},
                {"generation": "Gen12", "result": "+15.723% median", "detail": "The exact accepted all-CTA/all-3,200-tile topology still perturbed the hot path when internal values were stored.", "accepted": False},
                {"generation": "Gen13", "result": f"+{rejected_gen13['median_overhead_pct']:.3f}% median / +{rejected_gen13['p90_overhead_pct']:.3f}% p90", "detail": "Register-only E3/E4 clocks with deferred flushing still exceeded the 5% gate while preserving 168 registers, 12 barriers, zero stack/spills, and the same shared-memory plan. Stop condition reached.", "accepted": False},
            ],
        },
    }


def write_outputs(
    payload: dict[str, Any], output_json: Path, template: Path, output_html: Path
) -> None:
    # Use the exact same browser-safe bytes in the sidecar and embedded script.
    # This makes a byte comparison stronger than the validator's object-equality
    # check while retaining protection against an accidental ``</script>``.
    serialized = json.dumps(
        payload, separators=(",", ":"), ensure_ascii=False
    ).replace("<", "\\u003c")
    output_json.write_text(serialized, encoding="utf-8")
    document = template.read_text(encoding="utf-8")
    if document.count("__TIMELINE_JSON__") != 1:
        raise ValueError("HTML template must contain exactly one __TIMELINE_JSON__ marker")
    document = document.replace("__TIMELINE_JSON__", serialized)
    document = document.replace("__GENERATED_AT__", payload["artifact"]["generated_at"])
    output_html.write_text(document, encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=root / "probe_manifest.json")
    parser.add_argument("--output-json", type=Path, default=root / "timeline_data.json")
    parser.add_argument("--template", type=Path, default=root / "index.template.html")
    parser.add_argument("--output-html", type=Path, default=root / "index.html")
    parser.add_argument(
        "--wg2-phase-json",
        type=Path,
        help="Optional accepted generation-9 WG2 same-launch full-axis analysis JSON",
    )
    parser.add_argument(
        "--build-wg2-phase-analysis-from-runs",
        type=Path,
        metavar="RUNS_ROOT",
        help="Validate the generation-9 full-axis binary × three repeats and write the compact analysis before generating the page",
    )
    parser.add_argument(
        "--wg2-gen8-rejection",
        type=Path,
        help="Accepted generation-8 rejection record required by the generation-9 analyzer",
    )
    parser.add_argument(
        "--wg2-resource-manifest",
        type=Path,
        help="Accepted generation-9 ID40 compile/resource evidence manifest",
    )
    parser.add_argument(
        "--wg2-expected-samples-per-repeat",
        type=int,
        default=100,
        help="Pinned full-axis samples per repeat; generation 9 requires 100",
    )
    args = parser.parse_args()
    if args.build_wg2_phase_analysis_from_runs:
        if args.wg2_expected_samples_per_repeat != 100:
            raise ValueError(
                "generation-9 acceptance is pinned to 100 samples per repeat"
            )
        compact_path = (
            args.wg2_phase_json.resolve()
            if args.wg2_phase_json
            else (
                args.build_wg2_phase_analysis_from_runs.resolve()
                / "accepted_full_axis_analysis.json"
            )
        )
        analyzer = root.parent / "analyze_wg2_gen9.py"
        command = [
            sys.executable,
            str(analyzer),
            "--runs-root",
            str(args.build_wg2_phase_analysis_from_runs.resolve()),
            "--gen8-rejection",
            str(
                (
                    args.wg2_gen8_rejection
                    or root.parent
                    / "runs-wg2-gen8"
                    / "rejected_cumulative_axis_analysis.json"
                ).resolve()
            ),
            "--output",
            str(compact_path),
        ]
        if args.wg2_resource_manifest:
            command.extend(
                [
                    "--resource-manifest",
                    str(args.wg2_resource_manifest.resolve()),
                ]
            )
        subprocess.run(command, check=True)
        args.wg2_phase_json = compact_path
    payload = build_payload(
        args.manifest.resolve(),
        args.wg2_phase_json.resolve() if args.wg2_phase_json else None,
    )
    write_outputs(payload, args.output_json.resolve(), args.template.resolve(), args.output_html.resolve())
    selected = payload["flashmla_composite"]["accepted_scaffold"]["selected_critical_cta"]
    print(
        json.dumps(
            {
                "output_json": str(args.output_json.resolve()),
                "output_html": str(args.output_html.resolve()),
                "scaffold_us": payload["duration_seconds"] * 1_000_000,
                "selected_partition": selected["partition"],
                "selected_cta_us": selected["duration_us"],
                "wg2_service_union_us": selected["observed_region_accounting"]["wg2_service_union_us"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
