"""Reproduce stage and same-service post-scheduler delays from saved exact traces."""
import collections
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'evidence/spike-traces'
x = json.loads((D / 'joined.json').read_text())
spans = collections.defaultdict(list)
for s in x['spans']:
    spans[s['trace_id']].append(s)
requests, gaps = [], []
for c in x['cohorts']:
    # Alex places the suffix of its synthetic request ID in x-request-id.
    request_suffix = c['request_id'].removeprefix('trace-request-')
    ids = {s['trace_id'] for s in x['lookup'] if s.get('x_request_id') == request_suffix}
    assert len(ids) == 1, (c['send_index'], ids)
    ss = spans[ids.pop()]
    by_id = {s['span_id']: s for s in ss}
    def scheduler_parent(s):
        seen = set()
        while s.get('reference_parent_span_id') in by_id:
            sid = s['reference_parent_span_id']
            assert sid not in seen
            seen.add(sid)
            s = by_id[sid]
            if 'Scheduler' in s['operation_name']:
                return s
        return None
    stages = {}
    for s in ss:
        if s['operation_name'] not in ('prefill_bootstrap','prefill_waiting','prefill_forward','prefill_transfer_kv_cache','decode_bootstrap','decode_transferred','decode_waiting','decode_forward'):
            continue
        parent = scheduler_parent(s)
        if parent is None:
            continue
        if s['operation_name'].startswith('prefill_') and parent.get('pp_rank') != '0':
            continue
        assert s['operation_name'] not in stages
        stages[s['operation_name']] = s['duration'] / 1e6
    assert len(stages) == 8, (c['send_index'], stages)
    tpot_ms = (c['last_generation_time']-c['first_generation_time'])*1000/(c['output_tokens']-1)
    requests.append({'request_id':c['request_id'], 'send_index':c['send_index'], 'cohort':c['cohort'], 'ttft':c['ttft'], 'client_tpot_ms':tpot_ms, 'stages_s':stages})
    sched = [s for s in ss if s['operation_name'].startswith('Decode Scheduler')]
    assert len(sched) == 1
    sched = sched[0]
    req = by_id[sched['reference_parent_span_id']]
    assert req['operation_name'].startswith('decode Req ')
    assert req['service_name'] == sched['service_name']
    gaps.append({'send_index':c['send_index'], 'cohort':c['cohort'], 'post_scheduler_decode_request_ms':(req['end_time']-sched['end_time'])/1e6, 'same_service':True})
summary = []
for cohort in dict.fromkeys(c['cohort'] for c in requests):
    rows = [r for r in requests if r['cohort'] == cohort]
    summary.append({'cohort':cohort,'n':len(rows),'stages_mean_s':{k:statistics.mean(r['stages_s'][k] for r in rows) for k in sorted(rows[0]['stages_s'])}})
for name, result in [('decomposition',{'summary':summary,'requests':requests}),('post-scheduler-delays',gaps)]:
    prior = json.loads((D / (name+'.json')).read_text())
    assert prior == result, 'Saved calculation differs: '+name
    (D / (name+'-reproduced.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'requests':len(requests),'stage_and_same_service_gap_results_reproduced':True,'summary':summary}))
