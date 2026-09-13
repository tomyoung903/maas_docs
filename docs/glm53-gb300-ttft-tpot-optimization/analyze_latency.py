import bisect
import collections
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = Path('/mnt/HPC/tom/pd-queue-overnight-20260912.twotxxas')

def percentile(values, q):
    a = sorted(values)
    if not a:
        return None
    pos = (len(a)-1)*q/100
    i = math.floor(pos)
    return a[i] + (a[min(i+1,len(a)-1)]-a[i])*(pos-i)

def tpot(x):
    if not x['success'] or (x.get('output_tokens') or 0) <= 1:
        return None
    return 1000*(x['last_generation_time']-x['first_generation_time'])/(x['output_tokens']-1)

report = {'definitions': {'portal':'20-second trailing completion-time window, one-second steps; minimum three samples; linear percentile',
                         'previous_acceptance':'60-second arrival-time windows',
                         'tpot':'1000*(last_generation_time-first_generation_time)/(output_tokens-1), successful requests with output_tokens>1',
                         'contract':'TTFT P50/P75/P90/P99 targets 4/8/12/30 seconds; average missing. Three OTPS/TPOT pairs do not fully specify five columns. Threshold fractions are descriptive, not complete contractual certification.'},'runs':[]}
arms = json.loads((OLD/'evidence/completed-arm-comparison.json').read_text())['arms']
if sys.argv[1:]:
    arms = [{'arm':'follow-up', 'run_id':rid} for rid in sys.argv[1:]]
for arm in arms:
    rid = arm['run_id']; d = ROOT/'evidence'/rid
    xs = [json.loads(l) for l in (d/'timing-events.jsonl').open()]
    s = json.loads((d/'summary.json').read_text()); ts = json.loads((d/'timeseries.json').read_text())['distribution_sliding']
    assert len(xs) == s['requests']['total'] == 5921
    base = ts['base_time']; good = [x for x in xs if x['success']]
    pairs = [(tpot(x),x) for x in good if tpot(x) is not None]
    vals = [v for v,x in pairs]
    assert abs(percentile(vals,99)-s['latency_ms']['tpot']['p99']) < 1e-7
    ordered = sorted(good,key=lambda x:x['end_time']); ends = [x['end_time']-base for x in ordered]
    checked = 0
    for p in ts['points']:
        sample = ordered[bisect.bisect_left(ends,p['t']-ts['window_s']):bisect.bisect_right(ends,p['t'])]
        assert len(sample) == p['n_samples']
        if len(sample)<3:
            continue
        for metric,q in [('ttft',50),('tpot',99)]:
            values = [x['ttft']*1000 for x in sample if x.get('ttft') is not None] if metric=='ttft' else [tpot(x) for x in sample if tpot(x) is not None]
            calc = percentile(values,q)
            assert abs(calc-p[metric]['p'+str(q)]) < 1e-7
        checked += 1
    valid = [p for p in ts['points'] if p['ttft']['p50'] is not None]
    peak_ttft = max(valid,key=lambda p:p['ttft']['p50']); peak_tpot = max(valid,key=lambda p:p['tpot']['p99'])
    tail = []
    for v,x in sorted(pairs,key=lambda z:z[0],reverse=True)[:25]:
        tail.append({k:x.get(k) for k in ['request_id','source_request_id','send_index','output_tokens','input_tokens','cached_tokens','ttft']} |
                    {'tpot_ms':v,'end_s':x['end_time']-base,'first_s':x['first_generation_time']-base,'last_s':x['last_generation_time']-base,'max_itl_ms':max(x.get('itl') or [0])*1000})
    row = dict(arm=arm['arm'],run_id=rid,requests=len(xs),successes=len(good),failures=len(xs)-len(good),
               ttft_global_ms=s['latency_ms']['ttft'],tpot_global_ms=s['latency_ms']['tpot'],
               worst_portal_ttft=peak_ttft,worst_portal_tpot=peak_tpot,
               portal_points_p50_above4=sum(p['ttft']['p50']>4000 for p in valid),
               portal_points_tpot_p99_above40=sum(p['tpot']['p99']>40 for p in valid),
               tpot_requests_above40=sum(v>40 for v in vals),tpot_requests_above80=sum(v>80 for v in vals),
               tpot_zero_span=sum(v==0 for v in vals),recomputed_chart_points=checked,
               thresholds={str(th):{'count_le':sum(v<=th for v in vals),'eligible':len(vals),'fraction_le':sum(v<=th for v in vals)/len(vals)} for th in (18,33,40)},
               ttft_threshold_fractions={str(th):sum(x['ttft']<=th for x in good)/len(good) for th in (4,8,12,30)},
               worst_requests=tail)
    report['runs'].append(row)
name = 'latency-comparison-' + '-'.join(sys.argv[1:]) if sys.argv[1:] else 'latency-comparison'
(ROOT/'evidence'/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{k:x[k] for k in ['run_id','tpot_requests_above40','tpot_requests_above80','portal_points_p50_above4','portal_points_tpot_p99_above40','recomputed_chart_points']} for x in report['runs']],indent=2))
