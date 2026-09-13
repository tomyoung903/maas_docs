"""Summarize CPU samples without interpreting compressed sample time as wall time."""
import collections
import json
from pathlib import Path
import sys

A = Path(sys.argv[1]).resolve()
D = A / 'cpu-stacks'
out = {'limitation':'Nonblocking py-spy samples are conditional on successful reads. Thread profiles use synthetic weights; neither their summed weights nor positions establish exact wall-clock CPU or stall durations. Native stacks were not captured.', 'processes':[]}
for pid in (1,366):
    x = json.loads((D/f'pid{pid}.json').read_text())
    fs = x['shared']['frames']
    def label(i):
        f = fs[i]
        return f"{f['name']} ({f.get('file','')}:{f.get('line',0)})"
    rows = []
    for p in x['profiles']:
        inclusive,leaf = collections.Counter(),collections.Counter()
        groups=[]
        for idx,s in enumerate(p['samples']):
            inclusive.update(set(s))
            if s:
                leaf[s[-1]] += 1
                if groups and groups[-1]['stack'] == s:
                    groups[-1]['samples'] += 1
                else:
                    groups.append({'start_sample':idx,'samples':1,'stack':s})
        gc_ids = {i for i,f in enumerate(fs) if 'garbage' in f['name'].lower() or f['name'].lower() in ('gc','gc_collect','collect')}
        rows.append({'thread':p['name'],'samples':len(p['samples']), 'synthetic_weight_sum':sum(p['weights']),
                     'top_leaf':[{'frame':label(i),'count':n} for i,n in leaf.most_common(20)],
                     'top_inclusive':[{'frame':label(i),'count':n} for i,n in inclusive.most_common(25)],
                     'gc_related_samples':sum(bool(gc_ids.intersection(s)) for s in p['samples']),
                     'longest_identical_stacks':[dict(start_sample=g['start_sample'],samples=g['samples'],frames=[label(i) for i in g['stack']]) for g in sorted(groups,key=lambda g:g['samples'],reverse=True)[:12]]})
    out['processes'].append({'pid':pid,'exporter':x.get('exporter'),'sampler_log':(D/f'pid{pid}-sampler.log').read_text(),'threads':rows})
(D/'analysis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([{'pid':p['pid'],'sampler_log':p['sampler_log'],'main':[dict(thread=t['thread'],samples=t['samples'],gc_related_samples=t['gc_related_samples'],top_leaf=t['top_leaf'][:8]) for t in p['threads'] if 'MainThread' in t['thread']]} for p in out['processes']],indent=2))
