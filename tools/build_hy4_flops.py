#!/usr/bin/env python3
"""Rebuild the source-audited HY4 logical prefill ledger and static report."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/hy4-flops"
SOURCE = Path(__file__).with_name("hy4_flops")
REV = "66ca0e3bda0c9bc231a9408ad4adf69ce4644a95"
HF_REV = "705d81ee51566a186d645b74c974d642ef2828fe"
HF_URL = f"https://huggingface.co/tencent/Hy4-preview/resolve/{HF_REV}/config.json"
GLM_URL = "../glm52-flops/glm52_100k_prefill_execution_tree.html#execution-tree"
PUBLISHED_GLM = 10_945_320_321_466_784
N, H, A, RQ, RKV, DN, DR, DV, K = 100_000, 6144, 64, 2048, 512, 192, 64, 256, 2048
GLM_FULL = [0, 1, 2, *range(6, 78, 4)]
FILES = {
    "model": "python/sglang/srt/models/hunyuan_v4.py",
    "mla": "python/sglang/srt/models/deepseek_common/attention_forward_methods/forward_mla.py",
    "ffn": "python/sglang/srt/models/deepseek_v2.py",
    "indexer": "python/sglang/srt/layers/attention/dsa/dsa_indexer.py",
    "backend": "python/sglang/srt/layers/attention/dsa_backend.py",
    "ihc": "python/sglang/kernels/ops/layernorm/hy4_ihc.py",
    "logits": "python/sglang/srt/layers/logits_processor.py",
}


def capture(repo: Path) -> None:
    """Capture public config and hashes/anchors, never private source bodies."""
    OUT.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(["curl", "-fsSL", HF_URL])
    json.loads(raw)
    (OUT / "hy4-config.json").write_bytes(raw)
    evidence = {"revision": REV, "branch": "feat/hy4-preview-support", "date": "2026-09-09",
                "config_url": HF_URL, "config_sha256": hashlib.sha256(raw).hexdigest(), "files": {}}
    for key, path in FILES.items():
        body = subprocess.check_output(["git", "-C", str(repo), "show", f"{REV}:{path}"])
        anchors = {}
        for line, text in enumerate(body.decode().splitlines(), 1):
            stripped = text.strip()
            if stripped.startswith(("class ", "def ")):
                name = stripped.split()[1].split("(")[0].rstrip(":")
                anchors.setdefault(name, line)
        evidence["files"][key] = {"path": path, "sha256": hashlib.sha256(body).hexdigest(), "anchors": anchors}
    old = repo / "z_local/benchserving/mfu_metrics/build_glm52_flops_static_docs.py"
    evidence["glm_generator_sha256"] = hashlib.sha256(old.read_bytes()).hexdigest()
    (OUT / "source-audit.json").write_text(json.dumps(evidence, indent=2) + "\n")


def selected_pairs(n: int, k: int) -> int:
    m = min(n, k)
    return m * (m + 1) // 2 + max(0, n - k) * k


def shape(*dims: str | int) -> str:
    values = " &times; ".join(f"{d:,}" if isinstance(d, int) else d.replace("T", "<i>T</i>") for d in dims)
    return f'<span class="shape">&#8477;<sup>{values}</sup></span>'


def build_ledger(config: dict) -> dict:
    expected = {"hidden_size": H, "num_hidden_layers": 78, "num_attention_heads": A,
                "q_lora_rank": RQ, "kv_lora_rank": RKV, "qk_nope_head_dim": DN,
                "qk_rope_head_dim": DR, "v_head_dim": DV, "index_topk": K,
                "index_n_heads": 32, "index_head_dim": 128, "hc_mult": 4,
                "intermediate_size": 18432, "moe_intermediate_size": 2048,
                "n_routed_experts": 256, "num_experts_per_tok": 8,
                "n_shared_experts": 1, "vocab_size": 120832,
                "gated_mla": True, "learnable_sink": True}
    assert all(config.get(k) == v for k, v in expected.items()), "Config changed: audit the formulas first"
    full = [i for i, kind in enumerate(config["indexer_types"]) if kind == "full"]
    dense = [i for i, kind in enumerate(config["mlp_layer_types"]) if kind == "dense"]
    assert full == [0, 1, *range(5, 78, 4)] and dense == [0]
    c, s = N * (N + 1) // 2, selected_pairs(N, K)
    ops = []

    def op(key, title, scope, hy, glm, category, flow, formula, note, source="model", anchor="HYV4DecoderLayer"):
        if source == "mla" and anchor == "forward_mla":
            anchor = "forward_absorb_core" if key in {"vexpand", "outproj"} else "forward_absorb_prepare"
        formula = re.sub(r"(?<![A-Za-z])([THCS])(?![A-Za-z])", r"<i>\1</i>", formula)
        ops.append(dict(key=key, title=title, scope=scope, hy=hy, glm=glm,
                        category=category, flow=flow, formula=formula, note=note,
                        source=source, anchor=anchor))

    x = shape("T", H)
    carrier = shape("T", 4, H)
    op("embed", "Embedding lookup and carrier replication", "global", 0, 0, "Input / output",
       shape("T") + " &rarr; " + x + " &rarr; " + carrier, "0 floating-point operations",
       "Token lookup and copying are memory work. Four carrier streams are NOT four attention copies. No positional embedding GEMM.", anchor="HYV4Model")

    # Each sublayer has independent iHC gates. Post(attention) may fuse with pre(FFN).
    for prefix, name in [("ha", "Attention"), ("hf", "FFN")]:
        op(prefix + "_mix", name + " iHC gate projection", "all", N * 2 * (4 * H) * 8, 0, "iHC / residual",
           carrier + " &rarr; " + shape("T", 8), "2 &middot; T &middot; (4H) &middot; 8",
           "Flatten the four carrier vectors and project to four pre gates plus four post gates. FP32 projection weights in our source.", anchor="HYV4HCPreLayer")
        op(prefix + "_gates", "Carrier inverse RMS and gate nonlinearities", "all", N * (2 * 4 * H + 2 + 15 * 4), 0, "iHC / residual",
           shape("T", 8) + " &rarr; " + shape("T", 4) + " + " + shape("T", 4),
           "T [2(4H) + 2 + 15 &middot; 4]",
           "Inverse RMS: 2(4H)+2. Eight projection rescalings; four pre gates use 6 ops each and four post gates use 7. Post magnitude is 2; gate epsilon is added.", anchor="HYV4HCPreLayer")
        op(prefix + "_reduce", "Weighted four-stream reduction", "all", N * 7 * H, 0, "iHC / residual",
           carrier + " &rarr; " + x, "T (4H + 3H)",
           "Four multiplications and three additions per hidden coordinate. Attention/FFN consume only the reduced 6,144-wide vector.", anchor="HYV4HCPreLayer")
        op(prefix + "_norm", name + " input RMSNorm", "all", N * (4 * H + 2), N * (4 * H + 2), "Norms / RoPE",
           x + " &rarr; " + x, "T (4H + 2)", "RMSNorm follows carrier reduction. A fused iHC kernel may include it; it is counted once.", anchor="HYV4HCLayer")
        op(prefix + "_post", name + " iHC writeback / GLM residual add", "all", N * 8 * H, N * H, "iHC / residual",
           x + " + " + carrier + " &rarr; " + carrier, "HY4: 2 &middot; T &middot; 4H; GLM: T H",
           "For each stream: new carrier = old carrier + post gate times branch output. This replaces, not supplements, the GLM residual add.", anchor="HYV4HCLayer")

    op("qa", "Fused query-A and KV-A projection", "all", N * 2 * H * (RQ + RKV + DR), N * 2 * H * (RQ + RKV + DR), "MLA projections",
       x + " &rarr; " + shape("T", 2624), "2 T H (2,048 + 512 + 64)",
       "Split into query latent 2,048, KV latent 512, and shared RoPE key 64. This is one packed projection, not three independent copies.", "mla", "forward_mla")
    op("latent_norm", "Query / KV latent RMSNorm", "all", N * (4 * RQ + 2 + 4 * RKV + 2), N * (4 * RQ + 2 + 4 * RKV + 2), "Norms / RoPE",
       shape("T", 2048) + " + " + shape("T", 512), "T [(4 &middot; 2,048 + 2) + (4 &middot; 512 + 2)]",
       "Both latent vectors are normalized before their downstream projections.", "mla", "forward_mla")
    op("qb", "Query-B expansion", "all", N * 2 * RQ * A * (DN + DR), N * 2 * RQ * A * (DN + DR), "MLA projections",
       shape("T", 2048) + " &rarr; " + shape("T", 64, 256), "2 T &middot; 2,048 &middot; 64 &middot; (192 + 64)",
       "Each head gets a 192-dimensional non-RoPE query and a 64-dimensional RoPE query.", "mla", "forward_mla")
    op("absorb", "Absorb key-up weights into query", "all", N * 2 * A * DN * RKV, N * 2 * A * DN * RKV, "MLA projections",
       shape("T", 64, 192) + " &rarr; " + shape("T", 64, 512), "2 T &middot; 64 &middot; 192 &middot; 512",
       "Per-head BMM with the key slice of KV-B weights. No full 64-head key tensor is expanded for every cached token.", "mla", "forward_mla")
    op("rope", "Query and shared-key RoPE", "all", N * 3 * DR * (A + 1), N * 3 * DR * (A + 1), "Norms / RoPE",
       shape("T", 64, 64) + " + " + shape("T", 64), "3 T &middot; 64 &middot; (64 + 1)",
       "Three arithmetic operations per rotated scalar. Position-frequency constants differ; the counted rotation width is the same.", "mla", "forward_mla")
    op("kvstore", "Store this layer's compressed KV", "all", 0, 0, "MLA projections",
       shape("T", 512) + " + " + shape("T", 64) + " &rarr; layer-local KV records",
       "0 arithmetic FLOPs; 576 logical KV coordinates per token / layer",
       "Normalized compressed latent plus rotated key coordinates. Cache writes, layout conversion and quantization traffic are not counted here. The 4-stream residual carrier does not change these KV dimensions.", "backend", "forward_extend")

    for key, title, a, b, flow in [
        ("idxq", "Indexer query projection", RQ, 32 * 128, shape("T", 2048) + " &rarr; " + shape("T", 32, 128)),
        ("idxk", "Indexer key projection", H, 128, x + " &rarr; " + shape("T", 128)),
        ("idxw", "Indexer head-weight projection", H, 32, x + " &rarr; " + shape("T", 32))]:
        op(key, title, "full", N * 2 * a * b, N * 2 * a * b, "DSA setup / transforms", flow,
           f"2 T &middot; {a:,} &middot; {b:,}", "Only on a full indexer layer. A shared-index layer does not recompute these tensors.", "indexer", "Indexer")
    transforms = [("idxln", "Indexer key LayerNorm", 7 * 128 + 2, "7 &middot; 128 + 2"),
                  ("idxrope", "Indexer query / key RoPE", 3 * 64 * 33, "3 &middot; 64 &middot; 33"),
                  ("idxhad", "Indexer Hadamard and normalization", 33 * 128 * 8, "33 &middot; 128 &middot; (7 + 1)"),
                  ("idxscale", "Indexer head-weight scaling", 32 * 2, "32 &middot; 2")]
    for key, title, cost, formula in transforms:
        op(key, title, "full", N * cost, N * cost, "DSA setup / transforms", "32 query heads + one shared key; width 128",
           "T (" + formula + ")", "Hadamard has seven butterfly stages plus normalization. RoPE width is 64, not the full index-head width.", "indexer", "Indexer")
    op("idxscore", "Causal candidate scoring", "full", c * (2 * 32 * 128 + 2 * 32), c * (2 * 32 * 128 + 2 * 32), "DSA scoring",
       "C causal pairs &rarr; one score per pair", "C (2 &middot; 32 &middot; 128 + 2 &middot; 32)",
       "Dot products, ReLU, head weighting and reduction over 32 heads. ReLU comparisons are outside the FLOP ledger. Same 2h reduction convention as the GLM page.", "indexer", "Indexer")
    op("topk", "Top-2,048 selection and inter-layer ID reuse", "full", 0, 0, "DSA scoring",
       "C scores &rarr; " + shape("T", "&le;2,048") + " token IDs", "0 arithmetic FLOPs; comparison / movement work",
       "21 layers refresh; 57 reuse the preceding full layer's token IDs. Reusing IDs does NOT reuse attention outputs or skip that layer's KV projection.", "mla", "should_run_indexer")
    op("reuseids", "Reuse the preceding full layer's selected IDs", "shared_index", 0, 0, "DSA scoring",
       "Prior selected-position list &rarr; current layer's sparse attention", "0 selector recomputation FLOPs",
       "This is the alternative to a full indexer refresh. Current-layer attention still reads current-layer KV and recomputes every head output.", "mla", "should_run_indexer")

    pairs = s * A
    for key, title, cost, formula, flow, note in [
        ("qk", "Sparse query-key dot products", pairs * 2 * (RKV + DR), "2 S &middot; 64 &middot; (512 + 64)",
         shape("T", 64, 576) + " &middot; selected KV records", "The absorbed QK dot width is 576, not the unabsorbed 256."),
        ("score_scale", "Attention score scaling", pairs, "S &middot; 64", "One scalar per selected head/pair", "Scale each selected score before normalization."),
        ("softmax", "Selected softmax", 4 * pairs - N * A, "4 S &middot; 64 &minus; T &middot; 64", "Selected scores &rarr; probabilities", "Subtract max, exp, denominator sum, divide. Maximum comparisons are not FLOPs."),
        ("pv", "Sparse probability-value accumulation", pairs * 2 * RKV, "2 S &middot; 64 &middot; 512", shape("T", 64, 512), "Accumulate the compressed 512-wide latent value, not the final 256-wide head output.")]:
        op(key, title, "all", cost, cost, "Sparse MLA", flow, formula, note, "backend", "_forward_flashmla_sparse")
    op("sink", "Learnable sink in softmax denominator", "all", 3 * N * A, 0, "Attention sink",
       "64 learned logits; one extra denominator term per query/head", "3 T &middot; 64",
       "Add exp(sink minus row max) to the denominator; it has no key dot product and no value vector. This logical convention adds subtract, exp, add; comparisons excluded.", "backend", "_forward_flashmla_sparse")
    op("vexpand", "Latent-value to head-value expansion", "all", N * 2 * A * RKV * DV, N * 2 * A * RKV * DV, "MLA projections",
       shape("T", 64, 512) + " &rarr; " + shape("T", 64, 256), "2 T &middot; 64 &middot; 512 &middot; 256",
       "Per-head BMM with the value slice of KV-B weights; the attention gate is applied AFTER this expansion.", "mla", "forward_mla")
    op("gate", "Elementwise attention-gate projection", "all", N * 2 * H * A * DV, 0, "Attention gate",
       x + " &rarr; " + shape("T", 16384), "2 T &middot; 6,144 &middot; (64 &middot; 256)",
       "A separate learned 6,144 by 16,384 matrix in every layer, using the normalized attention input. Fallback projects earlier; HPC can defer and fuse the GEMM with gate application.", "model", "HYV4Attention")
    op("gate_apply", "Sigmoid gate times head outputs", "all", N * 4 * A * DV, 0, "Attention gate",
       shape("T", 64, 256) + " &rarr; " + shape("T", 16384), "4 T &middot; 64 &middot; 256",
       "One sigmoid (exp, add, divide) plus one multiplication per head-output element. There is a distinct gate for each of the 16,384 coordinates.", "model", "apply_attention_output_gate")
    op("outproj", "Attention output projection", "all", N * 2 * A * DV * H, N * 2 * A * DV * H, "MLA projections",
       shape("T", 16384) + " &rarr; " + x, "2 T &middot; 16,384 &middot; 6,144",
       "Return to hidden width before iHC writeback. Gate projection and output projection have the same logical GEMM cost, but opposite matrix dimensions.", "mla", "forward_mla")

    for key, title, factor in [("densegu", "Dense gate/up projections", 4), ("densedown", "Dense down projection", 2)]:
        op(key, title, "dense", factor * N * H * 18432, factor * N * H * 12288, "Dense FFN",
           (x + " &rarr; " + shape("T", 36864) if factor == 4 else shape("T", 18432) + " &rarr; " + x), f"{factor} T &middot; 6,144 &middot; 18,432",
           "HY4: only layer 0, intermediate width 18,432. GLM: layers 0-2, width 12,288.", "ffn", "DeepseekV2MLP")
    op("denseact", "Dense SiLU and multiply", "dense", N * 5 * 18432, N * 5 * 12288, "Dense FFN",
       "gate, up &rarr; SiLU(gate) &odot; up", "5 T &middot; 18,432",
       "Three sigmoid operations plus gate multiplication plus up multiplication. No routed-expert clamp on the dense layer.", "ffn", "DeepseekV2MLP")
    op("router", "MoE routing projection", "moe", N * 2 * H * 256, N * 2 * H * 256, "MoE routing / experts",
       x + " &rarr; " + shape("T", 256), "2 T &middot; 6,144 &middot; 256",
       "Score 256 routed experts; select eight. The shared expert is always active, not selected by this router.", "ffn", "DeepseekV2MoE")
    op("routerpost", "Routing sigmoid, bias, normalization and scale", "moe", N * 1047, N * 1047, "MoE routing / experts",
       shape("T", 256) + " &rarr; " + shape("T", 8), "T [3 &middot; 256 + 256 + 7 + 8 + 8]",
       "Top-8 comparisons and dispatch are separate. Fold the routed scale into eight normalized route weights in this logical ledger; actual backend may apply it later.", "ffn", "DeepseekV2MoE")
    op("dispatch", "Expert Top-8 and token dispatch", "moe", 0, 0, "MoE routing / experts",
       shape("T", H) + " &rarr; 8T routed token-expert assignments + T shared rows",
       "0 arithmetic FLOPs; comparisons, permutations and communication",
       "Eight routed copies are a logical assignment count, not necessarily one materialized tensor. Routing, grouped-GEMM layout and any EP all-to-all can consume substantial time despite zero FLOPs in this row.", "ffn", "DeepseekV2MoE")
    for tag, count, label in [("routed", 8, "Eight routed experts"), ("shared", 1, "One shared expert")]:
        for part, factor, desc in [("gu", 4, "gate/up"), ("down", 2, "down")]:
            op(tag + part, label + ": " + desc, "moe", N * factor * H * 2048 * count, N * factor * H * 2048 * count, "MoE routing / experts",
               (shape(f"{count}T", H) + " &rarr; " + shape(f"{count}T", 4096) if factor == 4 else shape(f"{count}T", 2048) + " &rarr; " + shape(f"{count}T", H)), f"{factor} T &middot; {count} &middot; 6,144 &middot; 2,048",
               "Count active token-expert assignments, not all 256 stored experts. Real grouped GEMM padding and routing imbalance are not included.", "ffn", "DeepseekV2MoE")
        op(tag + "act", label + ": SiLU and multiply", "moe", N * 5 * 2048 * count, N * 5 * 2048 * count, "MoE routing / experts",
           shape(f"{count}T", 2048), f"5 T &middot; {count} &middot; 2,048",
           "HY4 clamps ONLY routed expert gate/up inputs to limit 10. Shared-expert fusion is disabled because the shared branch must remain unclamped. Clamp comparisons are outside FLOPs.", "model", "shared_experts_fusion_disable_reason")
    op("combine", "Weighted routed reduction plus shared output", "moe", N * 16 * H, N * 16 * H, "MoE routing / experts",
       "8 weighted outputs + 1 unweighted shared output &rarr; " + x, "T [8H + 7H + H]",
       "Eight route multiplications, seven routed-sum additions, one shared addition. Unlike the old GLM ledger, omit the identity multiplication by the shared expert's unit weight.", "ffn", "DeepseekV2MoE")

    op("headmix", "Final iHC head reduction", "global", N * (2 * 4 * H + 2 + 2 * 4 * H * 4 + 7 * 4 + 7 * H), 0, "Input / output",
       carrier + " &rarr; " + x, "T [2(4H) + 2 + 2(4H)4 + 7 &middot; 4 + 7H]",
       "Final 24,576 to 4 gate projection, inverse RMS, sigmoid gates, weighted reduction. Runs on all prompt rows before logits selection, not just the final row.", "model", "HYV4HCHeadLayer")
    op("finalnorm", "Final RMSNorm", "global", N * (4 * H + 2), N * (4 * H + 2), "Norms / RoPE",
       x + " &rarr; " + x, "T (4H + 2)", "All prompt rows in the source forward. Fusion does not duplicate the arithmetic.", "model", "HYV4Model")
    op("lmhead", "Last-token LM head", "global", 2 * H * 120832, 2 * H * 154880, "Input / output",
       shape(1, H) + " &rarr; " + shape(1, 120832), "2 &middot; 6,144 &middot; 120,832",
       "One requested next-token logits row, no prompt logprobs. HY4 vocab 120,832 versus GLM 154,880. MTP/draft and subsequent decode steps excluded.", "logits", "LogitsProcessor")

    def layers(model, scope):
        if scope == "global":
            return []
        if scope == "all":
            return list(range(78))
        if scope == "full":
            return full if model == "hy" else GLM_FULL
        if scope == "shared_index":
            return [i for i in range(78) if i not in (full if model == "hy" else GLM_FULL)]
        if scope == "dense":
            return [0] if model == "hy" else [0, 1, 2]
        return list(range(1 if model == "hy" else 3, 78))

    categories = defaultdict(lambda: {"hy": 0, "glm": 0})
    layer_rows = [dict(layer=i, hy=0, glm=0, hy_full=i in full, glm_full=i in GLM_FULL,
                       hy_dense=i == 0, glm_dense=i < 3) for i in range(78)]
    for item in ops:
        for model in ["hy", "glm"]:
            ids = layers(model, item["scope"])
            item[model + "_layers"] = ids
            item[model + "_count"] = len(ids) if item["scope"] != "global" else 1
            item[model + "_total"] = item[model] * item[model + "_count"]
            categories[item["category"]][model] += item[model + "_total"]
            for i in ids:
                layer_rows[i][model] += item[model]
    totals = {m: sum(op[m + "_total"] for op in ops) for m in ["hy", "glm"]}
    reconciliation = N * 75 * H
    assert totals["glm"] + reconciliation == PUBLISHED_GLM
    for m in totals:
        assert sum(v[m] for v in categories.values()) == totals[m]
        assert sum(v[m] for v in layer_rows) + sum(op[m] for op in ops if op["scope"] == "global") == totals[m]
    return dict(tokens=N, candidate_pairs=c, selected_pairs=s, ops=ops, categories=dict(categories),
                layers=layer_rows, totals=totals, published_glm=PUBLISHED_GLM,
                reconciliation=reconciliation, hy_full=full, glm_full=GLM_FULL)


def group(title, children, note=""):
    return dict(title=title, children=children, note=note)


TREE = ["embed", group("Decoder stack: 78 layers", [
    group("iHC attention input", ["ha_mix", "ha_gates", "ha_reduce", "ha_norm"]),
    group("Sparse gated MLA attention", [
        group("Q / KV preparation", ["qa", "latent_norm", "qb", "absorb", "rope", "kvstore"]),
        group("DSA selector: 21 full, 57 shared-index layers", [
            group("Indexer setup", ["idxq", "idxk", "idxw", "idxln", "idxrope", "idxhad", "idxscale"]),
            "idxscore", "topk", "reuseids"]),
        group("Selected sparse attention", ["qk", "score_scale", "softmax", "sink", "pv"]),
        "vexpand", group("HY4 elementwise attention gate", ["gate", "gate_apply"]), "outproj"]),
    group("Attention writeback and iHC FFN input", ["ha_post", "hf_mix", "hf_gates", "hf_reduce", "hf_norm"],
          "post_pre may fuse attention writeback, next carrier reduction and FFN RMSNorm."),
    group("Feed-forward branch", [
        group("Dense MLP: layer 0 only", ["densegu", "denseact", "densedown"]),
        group("MoE: layers 1-77", ["router", "routerpost", "dispatch",
              group("Routed experts: 8 active / 256 stored", ["routedgu", "routedact", "routeddown"]),
              group("Shared expert: always active", ["sharedgu", "sharedact", "shareddown"]), "combine"])]),
    "hf_post"]), group("Final carrier reduction and normalization", ["headmix", "finalnorm"]), "lmhead"]


def keys(node):
    return [node] if isinstance(node, str) else [k for child in node["children"] for k in keys(child)]


def amount(n):
    if not n:
        return "0 FLOP"
    for unit, scale in [("PFLOP", 10**15), ("TFLOP", 10**12), ("GFLOP", 10**9)]:
        if abs(n) >= scale:
            return f"{n / scale:,.6f} {unit}"
    return f"{n:,} FLOP"


def source_link(evidence, file_key, anchor):
    record = evidence["files"][file_key]
    line = record["anchors"].get(anchor)
    assert line, (file_key, anchor)
    path = record["path"]
    url = f"https://git.luchentech.com/maas/sglang/-/blob/{REV}/{path}#L{line}"
    return f'<a href="{url}">{Path(path).name}:{line}:1</a>'


def render_tree(ledger, evidence):
    ops = {op["key"]: op for op in ledger["ops"]}

    def render(node, number, depth):
        ks = keys(node)
        value = sum(ops[k]["hy_total"] for k in ks)
        attrs = f'data-keys="{",".join(ks)}"'
        total = f'<span class="tree-cost" {attrs}>{amount(value)}</span>'
        if isinstance(node, str):
            item = ops[node]
            count = item["hy_count"]
            return f'''<details class="op" data-depth="{depth}" id="op-{node}">
<summary><span class="number">{number}</span><span>{item['title']}<small class="op-count" data-op="{node}">{count} logical instances</small></span>{total}</summary>
<div class="op-body"><div><span class="label">Tensor flow</span><div class="flow">{item['flow']}</div></div>
<div><span class="label">One active layer / invocation, 100K tokens</span><div class="formula">{item['formula']}</div><strong>{amount(item['hy'])}</strong></div>
<p>{item['note']}</p><p class="source">Source: {source_link(evidence, item['source'], item['anchor'])}</p></div></details>'''
        children = "".join(render(child, f"{number}.{i}", depth + 1) for i, child in enumerate(node["children"], 1))
        note = f'<p class="group-note">{node["note"]}</p>' if node["note"] else ""
        return f'''<details class="group" data-depth="{depth}" open><summary><span class="number">{number}</span><span>{node['title']}</span>{total}</summary>{note}<div class="children">{children}</div></details>'''

    return "".join(render(node, str(i), 0) for i, node in enumerate(TREE, 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, metavar="SGLANG_REPO")
    args = parser.parse_args()
    if args.capture:
        capture(args.capture)
    evidence = json.loads((OUT / "source-audit.json").read_text())
    raw = (OUT / "hy4-config.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == evidence["config_sha256"]
    ledger = build_ledger(json.loads(raw))
    assert sorted(k for node in TREE for k in keys(node)) == sorted(op["key"] for op in ledger["ops"])
    cats = "".join(f'<tr><th scope="row">{html.escape(k)}</th><td>{v["glm"]/1e15:.9f}</td><td>{v["hy"]/1e15:.9f}</td><td class="delta">{(v["hy"]-v["glm"])/1e15:+.9f}</td></tr>' for k, v in ledger["categories"].items())
    layers = "".join(f'''<tr><th scope="row"><a href="#execution-tree" data-select-layer="{v['layer']}">{v['layer']}</a></th>
<td>{'dense' if v['hy_dense'] else 'MoE'} / {'full' if v['hy_full'] else 'shared'}</td>
<td>{'dense' if v['glm_dense'] else 'MoE'} / {'full' if v['glm_full'] else 'shared'}</td>
<td>{v['hy']/1e12:.6f}</td><td>{v['glm']/1e12:.6f}</td><td>{(v['hy']-v['glm'])/1e12:+.6f}</td></tr>''' for v in ledger["layers"])
    options = '<option value="all">Whole model</option>' + "".join(f'<option value="{i}">Layer {i}</option>' for i in range(78))
    representatives = {"model": "HYV4DecoderLayer", "mla": "DeepseekMLAForwardMixin", "ffn": "DeepseekV2MoE", "indexer": "Indexer", "backend": "_forward_flashmla_sparse", "ihc": "fused_hy4_ihc_pre", "logits": "LogitsProcessor"}
    sources = "".join(f'<li>{source_link(evidence, k, representatives[k])}<br><code>{v["sha256"]}</code></li>' for k, v in evidence["files"].items())
    total = ledger["totals"]
    gate = next(op for op in ledger["ops"] if op["key"] == "gate")["hy_total"]
    chart = '<svg viewBox="0 0 920 170" role="img" aria-labelledby="chart-title chart-desc"><title id="chart-title">Logical FLOP totals at 100,000 tokens</title><desc id="chart-desc">HY4 adds roughly fifteen percent useful arithmetic, mostly its elementwise attention-gate projection.</desc>'
    for i, model in enumerate(["glm", "hy"]):
        y = 30 + 75 * i
        width = total[model] / total["hy"] * 650
        chart += f'<text x="0" y="{y+21}" class="chart-label">{"GLM-5.2" if model == "glm" else "HY4"}</text><rect x="120" y="{y}" width="{width}" height="32" fill="{"#596775" if model == "glm" else "#087f76"}"/><text x="{130+width}" y="{y+21}" class="chart-label">{total[model]/1e15:.4f} P</text>'
        if model == "hy":
            gate_width = gate / total[model] * 650
            chart += f'<rect x="{770-gate_width}" y="{y}" width="{gate_width}" height="32" fill="#b44d36"/><text x="120" y="{y+54}" class="chart-note">Red segment: new attention-gate GEMM alone, {gate/1e15:.6f} PFLOP</text>'
    chart += "</svg>"
    replacements = {"TREE": render_tree(ledger, evidence), "OPTIONS": options, "CATEGORIES": cats, "LAYERS": layers,
                    "SOURCES": sources, "REV": REV, "HF_URL": HF_URL, "GLM_URL": GLM_URL,
                    "HY_TOTAL": f'{total["hy"]/1e15:.6f}', "GLM_TOTAL": f'{total["glm"]/1e15:.6f}',
                    "DELTA": f'{(total["hy"]-total["glm"])/1e15:.6f}', "PERCENT": f'{(total["hy"]/total["glm"]-1)*100:.2f}',
                    "C": f'{ledger["candidate_pairs"]:,}', "S": f'{ledger["selected_pairs"]:,}',
                    "HY_FULL": ", ".join(map(str, ledger["hy_full"])), "GLM_FULL": ", ".join(map(str, GLM_FULL)),
                    "CHART": chart, "CSS": (SOURCE / "style.css").read_text(),
                    "JS": (SOURCE / "report.js").read_text(),
                    "DATA": json.dumps(ledger).replace("</", "<\\/")}
    page = (SOURCE / "template.html").read_text()
    for k, v in replacements.items():
        page = page.replace("@@" + k + "@@", v)
    assert "@@" not in page
    (OUT / "index.html").write_text(page)
    (OUT / "ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print(json.dumps({"totals": total, "delta": total["hy"]-total["glm"], "operations": len(ledger["ops"]), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
