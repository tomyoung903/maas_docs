"""CPU-only prediction for a proposed L2-read-bound H20 GEMM."""
from dataclasses import replace
from copy import copy
from pathlib import Path
import json
import subprocess
import tilesight
from tilesight.arch.h20 import H20
from tilesight.modeling import program as sight
from tilesight.modeling.program.builder import KernelBuilder

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, required=True)
args = parser.parse_args()
out = args.output_dir
out.mkdir(parents=True, exist_ok=True)
m, n, k = 64, 9984, 2048
bm, bn, bk, stages = 16, 128, 64, 3
arch = H20().set_to_microbench()
assert arch.sm_count == 78
assert arch.ddr_bandwidth == 3_860_654_536_000
kb = KernelBuilder('main', grid={'n': n//bn, 'm': m//bm}, threads=128,
                   dispatch_order='linear_block_id',
                   metadata={'kernel': 'cutlass_mma_sync_cp_async',
                             'block_m': bm, 'block_n': bn, 'block_k': bk})
A = kb.tensor('A', (m, k), 'fp16')
B = kb.tensor('B', (k, n), 'fp16')
C = kb.tensor('C', (m, n), 'fp16')
As = kb.shared('A_s', (bm, bk), 'fp16', stages=stages)
Bs = kb.shared('B_s', (bk, bn), 'fp16', stages=stages)
acc = kb.fragment('acc', (bm, bn), 'fp32', carried=True)
Cr = kb.fragment('C_r', (bm, bn), 'fp16')
with kb.loop('k', k//bk, stages=stages) as loop:
    kb.copy(A['m', 'k'], As, name='load_A', engine='cp_async')
    kb.copy(B['k', 'n'], Bs, name='load_B', engine='cp_async')
    kb.gemm(As, Bs, acc, name='mma', compute_dtype='fp16', accumulation_dtype='fp32')
    with loop.epilogue():
        kb.cast(acc, Cr, name='cast_C', actor='epilogue')
        kb.copy(Cr, C['m', 'n'], name='store_C', engine='ldst')
program = kb.program(name='h20_l2_bound_candidate')
program = replace(program, launches=(replace(program.launches[0], residency=4),))
(out/'plan.json').write_text(json.dumps(sight.program_to_snapshot(program), indent=2))
result = sight.analyze(program, arch, options=sight.Options(cache='trace', ii_mode='periodic_best'))
snapshot = result.to_snapshot()
(out/'prediction.json').write_text(json.dumps(snapshot, indent=2))
launch = result.launch('main')
ops = []
for name, op in snapshot['ops']:
    for group in op['cost_groups']:
        ops.append(dict(name=name, count=group['count'], completion_us=group['completion_latency_s']*1e6,
                        resources_us={r:t*1e6 for r,t in group['service_s']}))
summary = dict(shape_mnk=[m,n,k], tile=[bm,bn,bk], stages=stages, residency=4,
               grid=[m//bm,n//bn], steps=k//bk, body_us=launch.kernel_body_s*1e6,
               with_launch_us=launch.total_s*1e6, waves=launch.waves,
               slots=launch.slots, ops=ops,
               flops=2*m*n*k, A_bytes=2*m*k, B_bytes=2*k*n, C_bytes=2*m*n,
               l2_read_bytes=(m//bm)*(n//bn)*(k//bk)*2*(bm*bk+bk*bn),
               arch={key:vars(arch)[key] for key in ['sm_count','l2_capacity','l2_bandwidth','ddr_bandwidth','fp16_tensor_flops','smem_bandwidth']},
               source_commit=subprocess.check_output(['git','-C',str(Path(tilesight.__file__).parent),'rev-parse','HEAD'], text=True).strip(),
               assumptions=['Full declared-access cache trace, initially cold',
                            'Four CTAs per SM, matching the earlier compiled 16x128x64 kernel',
                            'No new GPU measurement; no timing fitted to this shape'])
summary['rate_sensitivity'] = {}
for field in ['l2_bandwidth', 'ddr_bandwidth', 'fp16_tensor_flops']:
    alternate = copy(arch)
    setattr(alternate, field, getattr(alternate, field) * 2)
    modeled = sight.analyze(program, alternate, options=sight.Options(cache='trace', ii_mode='periodic_best'))
    summary['rate_sensitivity'][field + '_doubled'] = modeled.launch('main').kernel_body_s * 1e6
(out/'summary.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
