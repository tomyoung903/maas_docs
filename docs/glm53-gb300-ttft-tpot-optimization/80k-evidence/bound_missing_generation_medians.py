"""Sensitivity bounds for missing TTFT; preserve missing observations and acceptance."""
import bisect, datetime, hashlib, json, math, sys
from pathlib import Path
R=Path(__file__).resolve().parent;A=R/sys.argv[1]
assert A.parent==R and A.name in ['run-2p1d-80k','run-1p1d-80k']
final=json.loads((A/'replay/measured-final.json').read_text());rid=final['run_id']
D=R/'evidence'/rid
events=[json.loads(x) for x in (D/'timing-events.jsonl').read_text().splitlines()]
ts=json.loads((D/'timeseries.json').read_text())['distribution_sliding']
assert len(events)==final['summary']['requests']['total'] and all(x['success'] for x in events)
events.sort(key=lambda x:x['end_time']);ends=[x['end_time']-ts['base_time'] for x in events]
def bounds(sample,q):
    known=sorted(x['ttft'] for x in sample if x.get('ttft') is not None)
    missing=len(sample)-len(known)
    assert all(x>=0 and math.isfinite(x) for x in known)
    pos=(len(sample)-1)*q/100;i=math.floor(pos);j=math.ceil(pos);weight=pos-i
    # Lower bound: all unknown nonnegative latencies precede positive observations.
    lower=[0.0]*missing+known
    lo=lower[i]*(1-weight)+lower[j]*weight
    # Upper bound: all unknown latencies follow the known observations, even +infinity.
    # A bound is finite only if both interpolating ranks remain among known values.
    hi=None if j>=len(known) else known[i]*(1-weight)+known[j]*weight
    return dict(samples=len(sample),observed=len(known),unknown=missing,lower_s=lo,upper_s=hi)
points=[]
for p in ts['points']:
    sample=events[bisect.bisect_left(ends,p['t']-ts['window_s']):bisect.bisect_right(ends,p['t'])]
    assert len(sample)==p['n_samples']
    if len(sample)<3:continue
    b=bounds(sample,50);b.update(t=p['t'],observed_p50_s=p['ttft']['p50']/1000)
    assert b['lower_s']<=b['observed_p50_s']+1e-9
    assert b['upper_s'] is None or b['observed_p50_s']<=b['upper_s']+1e-9
    points.append(b)
finite=[p for p in points if p['upper_s'] is not None]
peak=max(finite,key=lambda p:p['upper_s'])
out=dict(sgt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),arm=A.name,run_id=rid,
    missing=sum(x.get('ttft') is None for x in events),windows=len(points),
    windows_with_missing=sum(p['unknown']>0 for p in points),maximum_missing_in_window=max(p['unknown'] for p in points),
    windows_without_finite_upper=len(points)-len(finite),worst_upper_bound=peak,
    all_window_p50_upper_bounds_below4=len(finite)==len(points) and all(p['upper_s']<4 for p in finite),
    global_bounds={str(q):bounds(events,q) for q in [50,75,90,99]},
    method='Same Alex20s trailing completion cohorts and linear percentile. All protocol successes included in rank count. Unknown latencies are placed before all nonnegative observations for the lower bound and after all finite observations for the upper bound. Missing timestamps are never assigned or written back. These are sensitivity bounds, not measured latency values.',
    acceptance_unchanged=True,
    caveat='Requests without visible generation still fail the response-coverage gate. A finite median upper bound does not make those requests successful or identify their actual TTFT.',
    provenance={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'timing-events.jsonl',D/'timeseries.json']},points=points)
dest=A/'LATENCY-SENSITIVITY-BOUNDS.json'
dest.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['points','provenance']}))
