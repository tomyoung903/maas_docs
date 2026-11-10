"""Capture every modeled L2 probability from TileSight's actual full trace."""
from dataclasses import replace
from pathlib import Path
import array,base64,hashlib,json,math,subprocess,sys
import tilesight
from tilesight.arch.h20 import H20
from tilesight.modeling.program import Options,Context
from tilesight.modeling.program.examples import gemm_program
from tilesight.modeling.program.cache_binding import build_cache_view,_level_configs
import tilesight.modeling.program.explicit_trace as trace
from tilesight.util.sdcm import sdcm

root=Path(__file__).resolve().parent
arch=H20().set_to_microbench()
program=gemm_program(m=4096,n=4096,k=4096,block_m=128,block_n=128,block_k=64,
                     stages=3,dtype='fp16',accumulation_dtype='fp32')
launch=replace(program.launches[0],requires_arch=('wgmma',),residency=1)
coords=launch.instance_coordinates()
assert coords==[(m,n) for m in range(32) for n in range(32)]
l2,_,_=_level_configs(arch,8192)
events=[]
Base=trace._WeightedLRUStack
class CaptureStack(Base):
    def access(self,identity,weight,refresh):
        distance,cold=super().access(identity,weight,refresh)
        probability=0.0 if cold else min(max(float(sdcm(distance,l2.associativity,l2.capacity_units)),0.0),1.0)
        events.append((identity,probability,cold,distance))
        return distance,cold
trace._WeightedLRUStack=CaptureStack
try:
    view=build_cache_view(launch,arch,Options(cache='trace'),Context(),78,1,78)
finally:
    trace._WeightedLRUStack=Base
values=array.array('f',[0.0]*(64*32*32*2))
cold_counts={'A':0,'B':0}
cursor=0
def consume(expected,k,m,n,kind):
    global cursor
    identity,p,cold,distance=events[cursor]; cursor+=1
    assert identity==expected,(cursor,identity,expected)
    values[((k*32+m)*32+n)*2+kind]=p
    cold_counts[identity[0]]+=int(cold)
for wave_start in range(0,1024,78):
    wave=coords[wave_start:wave_start+78]
    for k in range(64):
        for m,n in wave: consume(('A',(m,k)),k,m,n,0)
        for m,n in wave: consume(('B',(k,n)),k,m,n,1)
    for m,n in wave:
        identity,p,cold,distance=events[cursor];cursor+=1
        assert identity==('C',(m,n))
assert cursor==len(events)==132096
assert cold_counts=={'A':2048,'B':2048}
means=[sum(values[i::2])/65536 for i in (0,1)]
for kind,entry in enumerate(view.report.per_access[:2]):
    assert abs(entry.l2_served_rate-means[kind])<1e-7
per_k=[[sum(values[((k*32+m)*32+n)*2+t] for m in range(32) for n in range(32))/1024
        for t in (0,1)] for k in range(64)]
if sys.byteorder!='little': values.byteswap()
raw=values.tobytes()
(root/'probabilities.f32').write_bytes(raw)
(root/'probabilities.b64').write_text(base64.b64encode(raw).decode())
meta=dict(shape=[4096,4096,4096],grid=[32,32,64],tile=[128,128,64],slots=78,
    layout='little-endian float32; index=(((k*32+m)*32+n)*2+operand), A=0 B=1',
    modeled_l2_hit_rates=means,per_k_means=per_k,compulsory_events=cold_counts,
    source_commit=subprocess.check_output(['git','-C',str(Path(tilesight.__file__).parent),'rev-parse','HEAD'],text=True).strip(),
    probabilities_sha256=hashlib.sha256(raw).hexdigest(),events=cursor,
    label='Full declared-plan cache trace; SDCM hit probabilities; no event sampling; not measured GPU traffic')
(root/'metadata.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(dict(means=means,cold=cold_counts,events=cursor,bytes=len(raw),
    per_k_min=[min(r[t] for r in per_k) for t in (0,1)],
    per_k_max=[max(r[t] for r in per_k) for t in (0,1)])))
