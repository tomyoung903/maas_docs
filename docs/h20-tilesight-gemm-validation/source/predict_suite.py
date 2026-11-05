"""Predeclare and predict five GEMMs on the corrected, unchanged H20 profile."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import tilesight
from tilesight.arch.h20 import H20
from tilesight.modeling import program as sight
from tilesight.modeling.program.examples import gemm_program

root=Path(__file__).resolve().parent
cases=json.loads((root/'cases.json').read_text())
arch=H20().set_to_microbench()
commit=subprocess.check_output(['git','-C',str(Path(tilesight.__file__).parent),'rev-parse','HEAD'],text=True).strip()
provenance=dict(tilesight_commit=commit,source=str(tilesight.__file__),
                cases_sha256=hashlib.sha256((root/'cases.json').read_bytes()).hexdigest(),
                arch={k:v for k,v in vars(arch).items() if isinstance(v,(int,float,str,bool))})
(root/'model-provenance.json').write_text(json.dumps(provenance,indent=2))
summary=[]
for case in cases:
    dest=root/case['name'];dest.mkdir(exist_ok=True)
    program=gemm_program(m=case['m'],n=case['n'],k=case['k'],block_m=128,block_n=128,block_k=64,
                         stages=3,dtype='fp16',accumulation_dtype='fp32')
    program=replace(program,launches=(replace(program.launches[0],requires_arch=('wgmma',),residency=1),))
    (dest/'plan.json').write_text(json.dumps(sight.program_to_snapshot(program),indent=2))
    result=sight.analyze(program,arch,options=sight.Options(cache='fast',ii_mode='periodic_best'))
    (dest/'prediction.json').write_text(json.dumps(result.to_snapshot(),indent=2))
    launch=result.launch('main')
    row=dict(case,body_us=launch.kernel_body_s*1e6,with_launch_us=launch.total_s*1e6,
             ctas=launch.physical_ctas,waves=launch.waves,slots=launch.slots,residency=launch.residency)
    summary.append(row);print(json.dumps(row),flush=True)
(root/'predictions.json').write_text(json.dumps(summary,indent=2))
