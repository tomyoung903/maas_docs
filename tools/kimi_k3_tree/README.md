# Kimi K3 100K text-prefill tree

The source of truth is `ledger.py` plus `../build_kimi_k3_tree.py`; do not edit the generated HTML/ledger directly.

Build and validate from the repository root:

```bash
python3 tools/build_kimi_k3_tree.py
python3 tools/build_kimi_k3_tree.py --check
python3 tools/test_kimi_k3_tree.py
```

The generator requires only the Python standard library. The numerical algebra check additionally uses NumPy:

```bash
python3 tools/kimi_k3_tree/verify_algebra.py
```

The generated pack is `docs/kimi-k3-flops/`. It includes the tree, overview, pinned official configuration, exact integer ledger, full 93-layer schedule, source/claim map, checkpoint-header audit, and validation evidence.

## Counting boundary

- One uncached 100,000-token text prefill and one next-token logits row.
- Expanded causal MLA, including all 192 QK coordinates despite NoPE.
- Sequential-equivalent KDA recurrence, **not executed chunk-prefill kernel FLOPs**.
- Expanded eager-reference Attention Residual arithmetic.
- GEMMs/dot contractions: two FLOPs per multiply-add; scalar/SFU conventions are explicit in the page.
- All learned text parameter objects count once; all 896 routed experts are owned, only 16 are executed per token.
- Logical state excludes packed storage overhead/quantization scales, vision, cache allocations, runtime replicas and draft models.
- No measured latency, throughput, hardware precision equivalence or runtime MFU claim.

The main logical total is 28,124,776,164,816,864 FLOPs. Switching only the MLA contraction to absorbed latent scan gives 45,819,673,112,016,864 FLOPs. These are alternatives, not additive subtrees.

## Evidence and independent verification

Official HF revision: `f831ab66814297da540d832a5235f8e904f29d06`.

Pinned SGLang revision: `cc1ecdadaf37e5d0a912ba3a68047a89dc453e1c`.

The generator checks the exact configuration SHA-256. `audit-reference.json` is a separately derived numerical ledger. `../test_kimi_k3_tree.py` maps every generated arithmetic leaf to its independent counterpart, checks unique ownership and all parent totals, parameter families and the complete layer schedule.

The source audit examined all 94 text-bearing checkpoint shard headers and matched 497,052 text tensor entries to the index without downloading weight payloads. The published header audit retains every header hash, per-layer totals and the exact treatment of packed expert weights. SGLang uses 96 entries from each checkpoint A-log tensor of length 128; all 69 inactive tails account for the 2,208-element difference between checkpoint and runtime-layout logical learned state.

## UI contract

`reference-style.css` and `reference-interactions.js` are preserved from the existing GLM-5.2 100K execution tree. `render.py` emits the same DOM classes and interactions. Every parent starts expanded, with clickable rows/keyboard buttons and three independently switchable columns. Do not redesign or modify the reference assets during a numerical update.

The page is reviewed in a normal desktop browser. Shared annotation markup is normalized by the repository helper during generation. The live root catalog discovers the new pack automatically; its Git metadata is refreshed when staging a publication.
