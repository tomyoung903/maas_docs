"""Reproduce instruction-family comparisons with the archived fixed memory rates.

PYTHONPATH=/path/to/TileSight python3 predict.py --output-dir /tmp/h20-prediction
Uses the pinned development revision recorded by this page. No GPU is needed.
"""
import argparse,json
from dataclasses import replace
from pathlib import Path
from tilesight.arch.h20 import H20
from tilesight.modeling import program as p
from tilesight.modeling.program.builder import KernelBuilder
from tilesight.modeling.program.examples import gemm_program
from tilesight.modeling.ops.throughput import ThroughputFallbackPolicy

args=argparse.ArgumentParser()
args.add_argument('--output-dir',type=Path,required=True)
out=args.parse_args().output_dir;out.mkdir(parents=True,exist_ok=True)
page=Path(__file__).resolve().parents[2]
rates=json.loads((page/'data/summary.json').read_text())['arch']
arch=H20().set_to_microbench()
for key,value in rates.items():setattr(arch,key,value)

def hmma(k):
    kb=KernelBuilder('main',grid={'n':78,'m':4},threads=128,dispatch_order='linear_block_id')
    a=kb.tensor('A',(64,k),'fp16');b=kb.tensor('B',(k,9984),'fp16');c=kb.tensor('C',(64,9984),'fp16')
    sa=kb.shared('A_s',(16,64),'fp16',stages=3);sb=kb.shared('B_s',(64,128),'fp16',stages=3)
    acc=kb.fragment('acc',(16,128),'fp32',carried=True);cr=kb.fragment('C_r',(16,128),'fp16')
    with kb.loop('k',k//64,stages=3) as loop:
        kb.copy(a['m','k'],sa,name='load_A',engine='cp_async')
        kb.copy(b['k','n'],sb,name='load_B',engine='cp_async')
        kb.gemm(sa,sb,acc,name='mma',compute_dtype='fp16',accumulation_dtype='fp32')
        with loop.epilogue():
            kb.cast(acc,cr,name='cast_C',actor='epilogue');kb.copy(cr,c['m','n'],name='store_C',engine='ldst')
    prog=kb.program(name='hmma_instruction_family_control')
    return replace(prog,launches=(replace(prog.launches[0],residency=4),))

rows=[]
for kind in ['hmma','wgmma']:
    for k in [512,1024,2048,4096]:
        prog=hmma(k) if kind=='hmma' else gemm_program(m=64,n=9984,k=k,block_m=64,block_n=128,block_k=64,stages=3,dtype='fp16',accumulation_dtype='fp32')
        if kind=='wgmma':prog=replace(prog,launches=(replace(prog.launches[0],requires_arch=('wgmma',),residency=1),))
        for label,rate in [('original',139.22),('independent',95.804007744 if kind=='hmma' else 142.650)]:
            options=p.Options(cache='trace',ii_mode='periodic_best',throughput_fallback=ThroughputFallbackPolicy(explicit_capacities=(('tensor.fp16.mma',rate*1e12),)))
            result=p.analyze(prog,arch,options=options)
            tag=f'{kind}-k{k}-{label}'
            (out/f'{tag}.json').write_text(json.dumps(result.to_snapshot(),indent=2))
            rows.append(dict(instruction_family=kind,k=k,rate_source=label,tflops=rate,body_us=result.launch('main').kernel_body_s*1e6))
(out/'summary.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
