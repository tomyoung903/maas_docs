"""Report original-output pressure and per-minute prompt means from preserved scalars."""
from pathlib import Path
import collections,json,sys
R=Path(__file__).resolve().parent;A=R/sys.argv[1];assert A.name in ['run-1p1d-80k','run-2p1d-80k']
x=json.loads((A/'ANALYSIS.json').read_text());rid=x['run_id'];events=[json.loads(s) for s in (R/'evidence'/rid/'timing-events.jsonl').read_text().splitlines()]
outputs=sorted(e['output_tokens'] or 0 for e in events if e['success'])
def pct(xs,q):
 a=(len(xs)-1)*q/100;i=int(a);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(a-i)
y={'run_id':rid,'protocol_successes':len(outputs),'total_output_tokens':sum(outputs),'mean_output_tokens':sum(outputs)/len(outputs),'max_output_tokens':max(outputs),'output_percentiles':{f'p{q}':pct(outputs,q) for q in [50,75,90,99]},'finish_reasons':dict(collections.Counter(e.get('finish_reason') for e in events)), 'last_completion_s':x['last_completion_s'],'note':'Actual outputs from this replay, not source logged response lengths. Original-output policy preserves original request settings and does not force a particular realized output length. Completion cohorts are not admission throughput.', 'admission_minute_mean_input': [{'start_s':m['start_s'],'admitted':m['admitted'],'mean_input_tokens':m['successful_input_tokens']/m['known_usage'] if m['known_usage'] else None} for m in x['admission_minutes']]}
with (A/'OUTPUT-DISTRIBUTION.json').open('x') as f:json.dump(y,f,indent=2)
print(json.dumps(y,indent=2))
