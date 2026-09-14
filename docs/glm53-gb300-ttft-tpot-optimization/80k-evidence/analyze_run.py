"""Recompute client latency/coverage and traffic from immutable exported request scalars."""
import bisect,collections,hashlib,json,math,sys
from pathlib import Path
N=Path(__file__).resolve().parent;A=N/sys.argv[1];P=A/'replay'
assert A.name in ['run-2p1d-80k','run-1p1d-80k']
C=N/('dataset-2p1d-candidate29' if A.name=='run-2p1d-80k' else 'dataset-1p1d-candidate01')
final=json.loads((P/'measured-final.json').read_text());rid=final['run_id'];D=N/'evidence'/rid
plan=json.loads((C/'candidate.json').read_text());expected={r['request_id']:r for r in plan['measured_requests']}
xs=[json.loads(s) for s in (D/'timing-events.jsonl').read_text().splitlines()];s=json.loads((D/'summary.json').read_text());ts=json.loads((D/'timeseries.json').read_text())['distribution_sliding'];base=ts['base_time']
assert len(xs)==s['requests']['total'] and len({x['request_id'] for x in xs})==len(xs)
assert {x['request_id'] for x in xs}<=set(expected)
assert len(xs)+s['requests']['not_recorded']==len(expected)
good=[x for x in xs if x['success']];meaningful=[x for x in good if x.get('ttft') is not None]
assert len(meaningful)==s['latency_ms']['ttft']['count']
def pct(a,q):
 a=sorted(a)
 if not a:return None
 z=(len(a)-1)*q/100;i=int(z);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i)
def tpot(x):
 if not x['success'] or (x.get('output_tokens') or 0)<=1 or x.get('first_generation_time') is None or x.get('last_generation_time') is None:return None
 return 1000*(x['last_generation_time']-x['first_generation_time'])/(x['output_tokens']-1)
vals=[tpot(x) for x in good if tpot(x) is not None]
assert abs(pct(vals,99)-s['latency_ms']['tpot']['p99'])<1e-6
ordered=sorted(good,key=lambda x:x['end_time']);ends=[x['end_time']-base for x in ordered];checked=0
for point in ts['points']:
 cohort=ordered[bisect.bisect_left(ends,point['t']-ts['window_s']):bisect.bisect_right(ends,point['t'])]
 assert len(cohort)==point['n_samples']
 if len(cohort)<3:continue
 for metric,q in [('ttft',50),('tpot',99)]:
  values=[x['ttft']*1000 for x in cohort if x.get('ttft') is not None] if metric=='ttft' else [tpot(x) for x in cohort if tpot(x) is not None]
  calc=pct(values,q);published=point[metric]['p'+str(q)]
  assert (calc is None and published is None) or (calc is not None and published is not None and abs(calc-published)<1e-6)
 checked+=1
valid=[p for p in ts['points'] if p['ttft']['p50'] is not None];bad=[p for p in valid if p['ttft']['p50']>=4000]
known=[x for x in good if x.get('cache_usage_available') and x.get('usage_received')]
mismatches=[{'request_id':x['request_id'],'prepared_tokens':expected[x['request_id']]['length'],'server_tokens':x['input_tokens'],'delta':x['input_tokens']-expected[x['request_id']]['length']} for x in known if x['input_tokens']!=expected[x['request_id']]['length']]
known_ids={x['request_id'] for x in known}
input_total=sum(x['input_tokens'] for x in known);cached_total=sum(x['cached_tokens'] for x in known)
cohorts=[]
for start in range(0,600,60):
 rows=[x for x in xs if start<=x['request_body_sent_time']-base<start+60];usable=[x for x in rows if x['request_id'] in known_ids]
 p=sum(x['input_tokens'] for x in usable);c=sum(x['cached_tokens'] for x in usable)
 cohorts.append({'start_s':start,'admitted':len(rows),'known_usage':len(usable),'offered_input_tokens':sum(x['est_prompt_tokens'] for x in rows),'successful_input_tokens':p,'successful_uncached_tokens':p-c,'hit_ratio':c/p if p else None,'ttft_p50_s':pct([x['ttft'] for x in usable if x.get('ttft') is not None],50)})
throughput=s['throughput'];generator={k:v for k,v in throughput.items() if any(w in k for w in ['valid','lag','delay','queue','overhead'])}
report={'run_id':rid,'state':final['state'],'candidate':str(C),'expected_requests':len(expected),'requests':s['requests'],'recorded_request_ids_unique_and_in_candidate':True,'runtime_vs_prepared_token_count_mismatches':len(mismatches),'runtime_vs_prepared_count_delta':sum(x['delta'] for x in mismatches),'runtime_vs_prepared_mismatch_examples':mismatches[:20],'known_usage_requests':len(known),'meaningful_requests':len(meaningful),'protocol_success_without_meaningful_generation':len(good)-len(meaningful),'ttft_ms':s['latency_ms']['ttft'],'ttft_percentiles_s':{f'p{q}':pct([x['ttft'] for x in meaningful],q) for q in [50,75,90,99]},'tpot_ms':s['latency_ms']['tpot'],'otps_finite_quantiles':{f'p{q}':pct([1000/v for v in vals if v>0],q) for q in [1,10,50,90,99]},'otps_finite_count':sum(v>0 for v in vals),'chart_window_s':ts['window_s'],'raw_recomputed_chart_points':checked,'valid_ttft_chart_points':len(valid),'points_p50_ge4s':len(bad),'points_p50_ge4s_during_admissions':sum(p['t']<=600 for p in bad),'points_p50_ge4s_during_drain':sum(p['t']>600 for p in bad),'worst_ttft_point':max(valid,key=lambda p:p['ttft']['p50']) if valid else None,'worst_tpot_point':max((p for p in ts['points'] if p['tpot']['p99'] is not None),key=lambda p:p['tpot']['p99'],default=None),'tpot_requests_gt40ms':sum(v>40 for v in vals),'tpot_requests_gt80ms':sum(v>80 for v in vals),'tpot_zero_span':sum(v==0 for v in vals),'tpot_threshold_fractions':{str(v):sum(t<=v for t in vals)/len(vals) for v in [18,33,40]},'input_tokens':input_total,'cached_tokens':cached_total,'uncached_tokens':input_total-cached_total,'hit_ratio':cached_total/input_total if input_total else None,'measured_mean_input':input_total/len(known) if known else None,'last_admission_s':max(x['request_body_sent_time']-base for x in xs),'last_completion_s':max(x['end_time']-base for x in xs),'admission_minutes':cohorts,'generator':generator,'bad_ttft_points':[{'t':p['t'],'n':p['n_samples'],'p50_ms':p['ttft']['p50']} for p in bad],'data_hashes':{str(p.relative_to(N)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [C/'candidate.json',D/'summary.json',D/'timeseries.json',D/'timing-events.jsonl']},'acceptance_note':'Raw client TTFT is the latency reference. Full acceptance requires all planned requests, meaningful output coverage, valid generator, intended live TPM/cache, and every eligible20s completion-window P50<4s including drain. Zero-span TPOT cannot establish finite OTPS.'}
with (A/'ANALYSIS.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:report[k] for k in ['run_id','state','requests','ttft_ms','tpot_ms','points_p50_ge4s','input_tokens','uncached_tokens','hit_ratio','last_completion_s','generator']},indent=2))
