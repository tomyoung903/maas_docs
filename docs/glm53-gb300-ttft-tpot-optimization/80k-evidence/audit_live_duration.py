"""Measure exact duration of live rolling-window deviations, without weighting boundary probes."""
import bisect,json,sys
from pathlib import Path
N=Path(__file__).resolve().parent;P=N/sys.argv[1]/'replay';d=json.loads((P/'observed-runtime-usage-projection.json').read_text());rows=d['measured_requests'];times=[r['offset_s'] for r in rows];pi=[0];pu=[0]
for r in rows:pi.append(pi[-1]+r['length']);pu.append(pu[-1]+r['ideal_uncached_tokens'])
p=d['parameters'];duration=p['minutes']*60-60;knots=sorted({0.,float(duration),*(v for t in times for v in [t,t-60] if 0<v<duration)});bad={'input':0.,'uncached':0.,'either':0.};spans=[]
for left,right in zip(knots,knots[1:]):
 mid=(left+right)/2;a=bisect.bisect_left(times,mid);b=bisect.bisect_left(times,mid+60);inp=pi[b]-pi[a];unc=pu[b]-pu[a]
 i=abs(inp/p['prompt_tpm']-1)>p['prompt_tolerance'];u=abs(unc/p['uncached_tpm']-1)>p['uncached_tolerance']
 for key,value in [('input',i),('uncached',u),('either',i or u)]:bad[key]+=(right-left)*value
 if i or u:
  reason=[i,u]
  if spans and spans[-1]['end_s']==left and spans[-1]['reason']==reason:spans[-1]['end_s']=right
  else:spans.append({'start_s':left,'end_s':right,'reason':reason})
out={'window_start_domain_s':[0,duration],'method':'Exact constant intervals between actual dispatch and dispatch-minus60 boundaries; excludes measure-zero endpoints, no grid/probe weighting.','seconds_outside_tolerance_by_window_start':bad,'fraction_of_window_start_time_outside':{k:v/duration for k,v in bad.items()},'spans':spans}
(P/'live-rolling-duration-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='spans'},indent=2))
