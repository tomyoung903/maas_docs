from dataclasses import replace
import argparse,hashlib,json,subprocess
from pathlib import Path
import tilesight
from tilesight.arch.h20 import H20
from tilesight.modeling import program as sight
from tilesight.modeling.program.builder import KernelBuilder
data=Path(__file__).resolve().parents[1]/'data'
parser=argparse.ArgumentParser(description='Reproduce the H20 memory-bound GEMM prediction on CPU.')
parser.add_argument('--output-dir', type=Path, default=data/'rerun')
parser.add_argument('--hbm-bps', type=float, help='Optional bandwidth sensitivity override, in decimal bytes/s.')
args=parser.parse_args()
root=args.output_dir
root.mkdir(parents=True,exist_ok=True)
cases=json.loads((data/'cases.json').read_text())
calibration=json.loads((data/'bandwidth-calibration.json').read_text())
arch=H20().set_to_microbench()
arch.ddr_bandwidth=args.hbm_bps if args.hbm_bps is not None else calibration['selected_bandwidth_Bps']
assert arch.ddr_bandwidth > 0 and arch.ddr_max_util == 1.0
metadata=json.loads((data/'kernel-metadata.json').read_text())
residency=metadata['max_active_blocks']
commit=subprocess.check_output(['git','-C',str(Path(tilesight.__file__).parent),'rev-parse','HEAD'],text=True).strip()
(root/'model-provenance.json').write_text(json.dumps(dict(tilesight_commit=commit,cases_sha256=hashlib.sha256((data/'cases.json').read_bytes()).hexdigest(),arch={k:v for k,v in vars(arch).items() if isinstance(v,(int,float,str,bool))},bandwidth_calibration_sha256=hashlib.sha256((data/'bandwidth-calibration.json').read_bytes()).hexdigest(),bandwidth_source='Independent cp.async microbenchmark' if args.hbm_bps is None else 'Explicit sensitivity override',residency_source='CUDA occupancy query on the compiled kernel, before measurement'),indent=2))
summary=[]
for case in cases:
    dest=root/case['name'];dest.mkdir(exist_ok=True)
    m,n,k=case['m'],case['n'],case['k']
    kb=KernelBuilder('main',grid={'n':n//128,'m':m//16},threads=128,dispatch_order='linear_block_id',metadata={'kernel':'cutlass_mma_sync_cp_async','block_m':16,'block_n':128,'block_k':64})
    A=kb.tensor('A',(m,k),'fp16'); B=kb.tensor('B',(k,n),'fp16'); C=kb.tensor('C',(m,n),'fp16')
    As=kb.shared('A_s',(16,64),'fp16',stages=3);Bs=kb.shared('B_s',(64,128),'fp16',stages=3)
    acc=kb.fragment('acc',(16,128),'fp32',carried=True);Cr=kb.fragment('C_r',(16,128),'fp16')
    with kb.loop('k',k//64,stages=3) as loop:
        kb.copy(A['m','k'],As,name='load_A',engine='cp_async')
        kb.copy(B['k','n'],Bs,name='load_B',engine='cp_async')
        kb.gemm(As,Bs,acc,name='mma',compute_dtype='fp16',accumulation_dtype='fp32')
        with loop.epilogue():
            kb.cast(acc,Cr,name='cast_C',actor='epilogue')
            kb.copy(Cr,C['m','n'],name='store_C',engine='ldst')
    program=kb.program(name='gemm_cp_async')
    program=replace(program,launches=(replace(program.launches[0],residency=residency),))
    (dest/'plan.json').write_text(json.dumps(sight.program_to_snapshot(program),indent=2))
    result=sight.analyze(program,arch,options=sight.Options(cache='fast',ii_mode='periodic_best'))
    snap=result.to_snapshot();(dest/'prediction.json').write_text(json.dumps(snap,indent=2))
    launch=result.launch('main')
    row=dict(case,body_us=launch.kernel_body_s*1e6,with_launch_us=launch.total_s*1e6,ctas=launch.physical_ctas,waves=launch.waves,slots=launch.slots,residency=launch.residency)
    summary.append(row);print(json.dumps(row),flush=True)
    ops=[]
    for name,op in snap['ops']:
        for g in op['cost_groups']:ops.append(dict(name=name,count=g['count'],us=g['completion_latency_s']*1e6,resources_us={key:value*1e6 for key,value in g['service_s']}))
    (root/'operation-times.json').write_text(json.dumps(ops,indent=2))
(root/'predictions.json').write_text(json.dumps(summary,indent=2))
