#!/usr/bin/env python3
"""Patch the container runtime for PP 100K prefill tracing.

This is intentionally small and reversible: it only edits files inside the
throwaway Docker container before launching SGLang.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path("/sgl-workspace/sglang/python/sglang/srt")


def patch_eager_runner() -> None:
    path = ROOT / "model_executor/runner/eager_runner.py"
    text = path.read_text(encoding="utf-8")
    old = "get_key_buffer(0)"
    new = "get_key_buffer(model_runner.start_layer)"
    if new in text:
        print(f"{path}: eager_runner already patched")
        return
    if old not in text:
        raise RuntimeError(f"{path}: expected {old!r} was not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"{path}: patched PP KV start layer")


TRACE_HELPER = r'''

# PP_TRACE_INJECTED_V1: lightweight JSONL runtime tracing for PP experiments.
def _pp_trace_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _pp_trace_len(value):
    try:
        if value is None:
            return 0
        return len(value)
    except Exception:
        return 0


def _pp_trace_int_list(value, limit=16):
    try:
        if value is None:
            return []
        if hasattr(value, "detach"):
            value = value.detach().cpu().tolist()
        else:
            value = list(value)
        return [_pp_trace_int(x) for x in value[:limit]]
    except Exception:
        return []


def _pp_trace_req(req):
    if req is None:
        return None
    prefix_len = _pp_trace_len(getattr(req, "prefix_indices", None))
    origin_len = _pp_trace_len(getattr(req, "origin_input_ids", None))
    fill_len = _pp_trace_int(getattr(req, "fill_len", 0))
    extend_len = _pp_trace_int(getattr(req, "extend_input_len", 0))
    return {
        "rid": str(getattr(req, "rid", "")),
        "extra_key": str(getattr(req, "extra_key", "")),
        "origin_len": origin_len,
        "prefix_len": prefix_len,
        "fill_len": fill_len,
        "extend_input_len": extend_len,
        "output_len": _pp_trace_len(getattr(req, "output_ids", None)),
        "cached_tokens": _pp_trace_int(getattr(req, "cached_tokens", 0)),
        "num_matched_prefix_tokens": _pp_trace_int(
            getattr(req, "num_matched_prefix_tokens", 0)
        ),
        "remaining_after_fill": max(origin_len - fill_len, 0),
    }


def _pp_trace_batch(batch):
    if batch is None:
        return None
    reqs = list(getattr(batch, "reqs", []) or [])
    req_info = [_pp_trace_req(req) for req in reqs]
    total_extend = sum((r or {}).get("extend_input_len", 0) for r in req_info)
    total_origin = sum((r or {}).get("origin_len", 0) for r in req_info)
    chunked_req = _pp_trace_req(getattr(batch, "chunked_req", None))
    extend_lens = _pp_trace_int_list(getattr(batch, "extend_lens", None))
    prefix_lens = _pp_trace_int_list(getattr(batch, "prefix_lens", None))
    seq_lens_cpu = _pp_trace_int_list(getattr(batch, "seq_lens_cpu", None))
    return {
        "forward_mode": str(getattr(batch, "forward_mode", "")),
        "batch_size": len(reqs),
        "total_extend_input_len": total_extend,
        "total_origin_len": total_origin,
        "batch_extend_num_tokens": _pp_trace_int(
            getattr(batch, "extend_num_tokens", 0)
        ),
        "batch_seq_lens_sum": _pp_trace_int(getattr(batch, "seq_lens_sum", 0)),
        "extend_lens": extend_lens,
        "prefix_lens": prefix_lens,
        "seq_lens_cpu": seq_lens_cpu,
        "prefill_input_ids_cpu_len": _pp_trace_len(
            getattr(batch, "prefill_input_ids_cpu", None)
        ),
        "input_ids_len": _pp_trace_len(getattr(batch, "input_ids", None)),
        "out_cache_loc_len": _pp_trace_len(getattr(batch, "out_cache_loc", None)),
        "contains_last_prefill_chunk": bool(
            getattr(batch, "contains_last_prefill_chunk", False)
        ),
        "chunked_req": chunked_req,
        "reqs": req_info,
    }


def _pp_trace_emit(scheduler, event, mb_id, batch=None):
    try:
        import json
        import os
        import time as _time

        root = os.environ.get("SGLANG_PP_TRACE_DIR")
        if not root or batch is None:
            return
        ps = getattr(scheduler, "ps", None)
        attn_tp_rank = _pp_trace_int(getattr(ps, "attn_tp_rank", 0))
        attn_cp_rank = _pp_trace_int(getattr(ps, "attn_cp_rank", 0))
        # TP ranks run the same scheduler decision. Keep one scheduler trace per
        # PP stage to make the evidence readable and avoid duplicate rows.
        if attn_tp_rank != 0 or attn_cp_rank != 0:
            return
        pp_rank = _pp_trace_int(getattr(ps, "pp_rank", 0))
        tp_rank = _pp_trace_int(getattr(ps, "tp_rank", 0))
        pp_group = getattr(scheduler, "pp_group", None)
        record = {
            "ts": _time.time(),
            "monotonic": _time.monotonic(),
            "pid": os.getpid(),
            "event": event,
            "mb_id": _pp_trace_int(mb_id),
            "pp_rank": pp_rank,
            "tp_rank": tp_rank,
            "attn_tp_rank": attn_tp_rank,
            "attn_cp_rank": attn_cp_rank,
            "is_first_rank": bool(getattr(pp_group, "is_first_rank", False)),
            "is_last_rank": bool(getattr(pp_group, "is_last_rank", False)),
            "pp_loop_size": _pp_trace_int(getattr(scheduler, "pp_loop_size", 0)),
            "pp_async_batch_depth": _pp_trace_int(
                getattr(getattr(scheduler, "server_args", None), "pp_async_batch_depth", 0)
            ),
            "chunked_prefill_size": _pp_trace_int(
                getattr(scheduler, "chunked_prefill_size", 0)
            ),
            "waiting_queue_len": _pp_trace_len(getattr(scheduler, "waiting_queue", None)),
            "batch": _pp_trace_batch(batch),
        }
        os.makedirs(root, exist_ok=True)
        path = os.path.join(root, f"pp{pp_rank}_tp{tp_rank}_pid{os.getpid()}.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    except Exception:
        return
'''


def patch_scheduler_pp_mixin() -> None:
    path = ROOT / "managers/scheduler_pp_mixin.py"
    text = path.read_text(encoding="utf-8")
    if "PP_TRACE_INJECTED_V1" not in text:
        marker = "logger = logging.getLogger(__name__)\n"
        if marker not in text:
            raise RuntimeError(f"{path}: logger marker was not found")
        text = text.replace(marker, marker + TRACE_HELPER, 1)

    select_old = (
        "                self.cur_batch: Optional[ScheduleBatch] = self.mbs[mb_id]\n"
        "                if self.cur_batch:\n"
    )
    select_new = (
        "                self.cur_batch: Optional[ScheduleBatch] = self.mbs[mb_id]\n"
        '                _pp_trace_emit(self, "select", mb_id, self.cur_batch)\n'
        "                if self.cur_batch:\n"
    )
    if select_new not in text:
        if select_old not in text:
            raise RuntimeError(f"{path}: select insertion point was not found")
        text = text.replace(select_old, select_new, 1)

    launch_old = (
        "                if self.cur_batch:\n"
        "                    result, self.launch_event = self._pp_launch_batch(\n"
        "                        mb_id,\n"
    )
    launch_new = (
        "                if self.cur_batch:\n"
        '                    _pp_trace_emit(self, "launch_begin", mb_id, self.cur_batch)\n'
        "                    result, self.launch_event = self._pp_launch_batch(\n"
        "                        mb_id,\n"
    )
    if launch_new not in text:
        if launch_old not in text:
            raise RuntimeError(f"{path}: launch insertion point was not found")
        text = text.replace(launch_old, launch_new, 1)

    launch_end_old = (
        "                        self.last_rank_comm_queue,\n"
        "                    )\n"
        "                if self.server_args.pp_async_batch_depth == 0:\n"
    )
    launch_end_new = (
        "                        self.last_rank_comm_queue,\n"
        "                    )\n"
        '                    _pp_trace_emit(self, "launch_end", mb_id, self.cur_batch)\n'
        "                if self.server_args.pp_async_batch_depth == 0:\n"
    )
    if launch_end_new not in text:
        if launch_end_old not in text:
            raise RuntimeError(f"{path}: launch-end insertion point was not found")
        text = text.replace(launch_end_old, launch_end_new, 1)

    run_old = "                result = self.run_batch(self.cur_batch, pp_proxy_tensors)\n"
    run_new = (
        '                _pp_trace_emit(self, "run_batch_enter", mb_id, self.cur_batch)\n'
        "                result = self.run_batch(self.cur_batch, pp_proxy_tensors)\n"
        '                _pp_trace_emit(self, "run_batch_return", mb_id, self.cur_batch)\n'
    )
    if run_new not in text:
        if run_old not in text:
            raise RuntimeError(f"{path}: run_batch insertion point was not found")
        text = text.replace(run_old, run_new, 1)

    path.write_text(text, encoding="utf-8")
    print(f"{path}: PP trace hooks installed")


def main() -> None:
    patch_eager_runner()
    patch_scheduler_pp_mixin()


if __name__ == "__main__":
    main()
