#!/usr/bin/env python3
"""Keep numerical sample evidence while removing repetitive trace strings."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--input', type=Path, required=True)
p.add_argument('--first-pass', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
d = json.loads(a.input.read_text())
first = {row['m']: row for row in json.loads(a.first_pass.read_text())['points']}
assert len(d['points']) == 259 and d['valid_sample_count'] == 7770
assert not d['rejected_samples']
assert d['run_metadata']['status'] == 'complete'
shifts = [abs(row['active_union_median_us'] / first[row['m']]['active_union_median_us'] - 1) * 100 for row in d['points']]
catalog = {}
for row in d['points']:
    assert row['sample_count'] == 30
    for sample in row['samples']:
        assert len(sample['kernels']) == 2
        for k in sample['kernels']:
            name = k.pop('name')
            kind = 'quantization' if 'per_token_group_quant' in name else 'gemm'
            catalog.setdefault(kind, set()).add(name)
            k['kind'] = kind

m = d['run_metadata']
m.update({
    'driver_version': '580.173.02', 'nvcc': '13.0.88', 'nsys_version': '2025.3.2.474',
    'triton': '3.6.0', 'power_limit_w': 1100,
    'clock_policy': 'Provider default clocks; no application clock lock or power-limit change',
    'scale_dtype': 'UE8M0 exponents packed in int32', 'scale_block': 128,
    'input_dtype': 'bfloat16', 'weight_dtype': 'float8_e4m3fn', 'output_dtype': 'bfloat16',
    'cuda_graphs': False, 'l2_flush': False,
    'kernel_count_validation': '7,770 / 7,770 samples have exactly one quantization and one GEMM kernel',
    'source_hashes': {'full_result_sha256': hashlib.sha256(a.input.read_bytes()).hexdigest()},
    'notes': [
        'Final pass uses three warmups immediately before each shape; one separate preflight call compiles kernels and checks correctness.',
        f'Two full sweeps: median absolute change {statistics.median(shifts):.3f}%; maximum {max(shifts):.3f}%. The final pass is plotted, not an average.',
        'The reference is from two GB300 nodes; this reproduction uses one B300. This is not a controlled pure-hardware comparison.',
        'Original DeepGEMM commit message is Bump to v0.1.3; the same fetched commit declares package version 2.5.0. The verified commit is retained as the identity.',
    ],
})
d['kernel_catalog'] = {k: sorted(v) for k, v in catalog.items()}
a.output.write_text(json.dumps(d, indent=2) + '\n')
print(json.dumps({'output': str(a.output), 'bytes': a.output.stat().st_size, 'repeatability_median_pct': statistics.median(shifts)}))
