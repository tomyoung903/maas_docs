# HY4 100K Prefill Ledger

This report is a logical source audit, not a GPU benchmark. Its existing
GLM-5.2 reference page is deliberately not modified.

Rebuild offline from the checked-in public config and source manifest:

```bash
python3 tools/build_hy4_flops.py
python3 -m unittest discover -s tools -p test_hy4_flops.py -v
```

The HTML template, CSS and browser controls live here. The Python builder
owns all integer arithmetic, operation metadata and tree membership.
`docs/hy4-flops/ledger.json` contains the complete per-operation, per-layer
and per-component ledger. Parent nodes sum their uniquely owned leaves.

Only when deliberately refreshing the evidence snapshot:

```bash
python3 tools/build_hy4_flops.py --capture /path/to/sglang
```

Capture reads the pinned SGLang revision with `git show`, without changing
the checkout. It downloads the pinned public Tencent config and saves
source hashes/anchors, not private source bodies. Changing model dimensions
or layer placement intentionally fails assertions until the formulas and
explanation are audited again.

GLM accounting reconciliation: the reference charged a unit multiplication
for the unweighted shared expert. Both ledgers here omit that identity
operation. Adding 46,080,000,000 FLOPs to our GLM total exactly reproduces
the published reference total. All source and numerical assumptions are
visible in the HTML; do not interpret the totals as precision-equivalent
FLOPs, executed padded FLOPs, hardware instructions, or measured latency.
