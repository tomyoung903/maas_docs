"""Record every cache probability for the memory-bound page's saved tile plan."""
import argparse,array,base64,hashlib,json,subprocess,sys
from pathlib import Path
import tilesight
from tilesight.arch.h20 import H20
from tilesight.modeling.program import Options,Context,program_from_snapshot
from tilesight.modeling.program.cache_binding import build_cache_view,_level_configs
import tilesight.modeling.program.explicit_trace as trace
from tilesight.util.sdcm import sdcm

parser=argparse.ArgumentParser()
parser.add_argument('--plan',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args();out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
raw_plan=args.plan.read_bytes()
program=program_from_snapshot(json.loads(raw_plan));launch=program.launches[0]
coords=launch.instance_coordinates();assert coords==[(0,n) for n in range(624)]
arch=H20().set_to_microbench();arch.ddr_bandwidth=3.860654536e12
l2,_,_=_level_configs(arch,2048)
events=[];Base=trace._WeightedLRUStack
class Capture(Base):
    def access(self,identity,weight,refresh):
        distance,cold=super().access(identity,weight,refresh)
        p=0.0 if cold else min(max(float(sdcm(distance,l2.associativity,l2.capacity_units)),0),1)
        events.append((identity,p,cold,distance))
        return distance,cold
trace._WeightedLRUStack=Capture
try:view=build_cache_view(launch,arch,Options(cache='trace'),Context(),312,4,78)
finally:trace._WeightedLRUStack=Base
values=array.array('f',[0]*(128*624*2));cold_count={'A':0,'B':0};cursor=0
for start in range(0,624,312):
    wave=coords[start:start+312]
    for k in range(128):
        for operand in (0,1):
            for m,n in wave:
                identity,p,cold,distance=events[cursor];cursor+=1
                assert identity==(('A',(m,k)) if operand==0 else ('B',(k,n)))
                values[(k*624+n)*2+operand]=p;cold_count[identity[0]]+=int(cold)
    for m,n in wave:
        assert events[cursor][0]==('C',(m,n));cursor+=1
assert cursor==len(events)==160368
assert cold_count=={'A':128,'B':79872}
mean=[sum(values[o::2])/79872 for o in (0,1)]
for o,r in enumerate(view.report.per_access[:2]):assert abs(mean[o]-r.l2_served_rate)<1e-7
if sys.byteorder!='little':values.byteswap()
raw=values.tobytes();(out/'probabilities.f32').write_bytes(raw)
(out/'probabilities.b64').write_text(base64.b64encode(raw).decode())
meta=dict(shape=[16,79872,8192],grid=[1,624,128],tile=[16,128,64],slots=312,sm_count=78,residency=4,
    l2_capacity_bytes=arch.l2_capacity,modeled_l2_hit_rates=mean,compulsory_events=cold_count,events=cursor,
    per_load_hbm_bytes=[r.traffic_per_request.ddr_read_bytes for r in view.report.per_access[:2]],
    layout='little-endian float32; index=(k*624+n)*2+operand; A=0,B=1',
    source_commit=subprocess.check_output(['git','-C',str(Path(tilesight.__file__).parent),'rev-parse','HEAD'],text=True).strip(),
    plan_sha256=hashlib.sha256(raw_plan).hexdigest(),probabilities_sha256=hashlib.sha256(raw).hexdigest(),
    label='Full declared-plan cache trace; no event sampling; SDCM probabilities, not measured GPU hits')
(out/'metadata.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(meta,indent=2))
