"""Verify shape identity, extract device durations, and compare frozen predictions."""
import csv
import json
from pathlib import Path
import sqlite3
import statistics

root=Path(__file__).resolve().parent
predictions=json.loads((root/'predictions.json').read_text())
def summarize(rows):
    times=sorted((r[1]-r[0])/1000 for r in rows)
    return dict(count=len(times),median_us=statistics.median(times),
                p10_us=times[int(len(times)*.1)],p90_us=times[int(len(times)*.9)],
                min_us=min(times),max_us=max(times))
comparison=[]
for p in predictions:
    d=root/p['name']
    log=[json.loads(line) for line in (d/'measurement.jsonl').read_text().splitlines()]
    meta=log[0]
    assert (meta['m'],meta['n'],meta['k'])==(p['m'],p['n'],p['k'])
    assert meta['tile']==[128,128,64] and meta['stages']==3
    assert meta['threads']==256 and meta['max_active_blocks']==p['residency']==1
    assert meta['grid']==[p['m']//128,p['n']//128,1]
    assert meta['sms']==78 and log[1]['correctness']=='PASS' and log[1]['mismatches']==0
    modes={r['mode']:r for r in log if 'mode' in r}
    c=sqlite3.connect(d/'profiling/device.sqlite')
    rows=c.execute('''SELECT k.start,k.end,s.value,k.gridX,k.gridY,k.blockX,
                            k.registersPerThread,k.dynamicSharedMemory,k.localMemoryPerThread
                     FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName
                     ORDER BY k.start''').fetchall()
    first=next(r for r in rows if 'cutlass::device_kernel<' in r[2])
    rows=[r for r in rows if r[2]==first[2]]
    assert len(rows)==203,(p['name'],len(rows))
    assert all(r[3:6]==(p['m']//128,p['n']//128,256) and r[8]==0 for r in rows)
    trace=dict(warm=summarize(rows[101:152]),cold=summarize(rows[152:203]),
               correctness_launches=1,warmup_launches=100,
               dynamic_smem=first[7],registers_per_thread=first[6])
    (d/'profiling/kernel-times.json').write_text(json.dumps(trace,indent=2))
    with (d/'profiling/kernel-times.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['index','phase','device_us'])
        for i,r in enumerate(rows):
            w.writerow([i,'correctness' if i==0 else 'warmup' if i<101 else 'warm' if i<152 else 'cold',(r[1]-r[0])/1000])
    measured=trace['cold']['median_us']
    row=dict(name=p['name'],m=p['m'],n=p['n'],k=p['k'],ctas=p['ctas'],waves=p['waves'],
             predicted_us=p['body_us'],device_cold_us=measured,device_warm_us=trace['warm']['median_us'],
             cold_p10_us=trace['cold']['p10_us'],cold_p90_us=trace['cold']['p90_us'],
             event_cold_us=modes['cold']['median_us'],event_warm_us=modes['warm']['median_us'],
             graph_per_kernel_us=modes['graph_per_kernel']['median_us'],
             error_pct=100*(p['body_us']-measured)/measured,
             correctness='PASS',output_elements=log[1]['elements'])
    comparison.append(row)
with (root/'comparison.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
out=dict(cases=comparison,mean_absolute_percent_error=statistics.mean(abs(r['error_pct']) for r in comparison),
          max_absolute_percent_error=max(abs(r['error_pct']) for r in comparison),
          error_definition='100 * (prediction - measured cold device duration) / measured cold device duration')
(root/'comparison.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
