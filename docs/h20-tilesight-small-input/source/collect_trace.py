"""Extract device-only timings using the benchmark's exact GEMM launch manifest."""
import argparse,csv,json,sqlite3,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--sqlite',type=Path,required=True);p.add_argument('--launches',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
with a.launches.open() as f: manifest=list(csv.DictReader(f))
assert [int(r['gemm_index']) for r in manifest]==list(range(len(manifest)))
c=sqlite3.connect(a.sqlite)
rows=c.execute('''SELECT k.start,k.end,s.value,k.gridX,k.gridY,k.blockX,k.registersPerThread,k.dynamicSharedMemory,k.localMemoryPerThread
FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start''').fetchall()
name=next(r[2] for r in rows if 'cutlass::Kernel<' in r[2])
selected=[(i,r) for i,r in enumerate(rows) if r[2]==name]
assert len(selected)==len(manifest),(len(selected),len(manifest))
assert all(r[5:]==(128,64,55296,0) for _,r in selected),selected[0][1]
measurements=[]
for manifestrow,(ix,row) in zip(manifest,selected):
 if manifestrow['phase']!='measure':continue
 prior=rows[ix-1] if ix else None
 index=int(manifestrow['gemm_index'])
 priming=selected[index-1][1]
 assert manifest[index-1]['phase']=='prime' and manifest[index-1]['mode']==manifestrow['mode']
 measurements.append({**manifestrow,'device_us':(row[1]-row[0])/1000,'prime_device_us':(priming[1]-priming[0])/1000,'preceding_kernel':prior[2] if prior else '', 'preceding_kernel_us':(prior[1]-prior[0])/1000 if prior else None,'gap_after_preceding_kernel_us':(row[0]-prior[1])/1000 if prior else None})
a.output.mkdir(parents=True,exist_ok=True)
with (a.output/'device-samples.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(measurements[0]));w.writeheader();w.writerows(measurements)
summary={}
for mode in sorted(set(r['mode'] for r in measurements)):
 group=[r for r in measurements if r['mode']==mode]
 values=sorted(r['device_us'] for r in group)
 summary[mode]={'samples':len(values),'median_us':statistics.median(values),'p10_us':values[len(values)//10],'p90_us':values[len(values)*9//10],'min_us':min(values),'max_us':max(values),'median_prime_us':statistics.median(r['prime_device_us'] for r in group),'median_gap_after_preceding_kernel_us':statistics.median(r['gap_after_preceding_kernel_us'] for r in group),'median_preceding_kernel_us':statistics.median(r['preceding_kernel_us'] for r in group)}
result={'gemm_launches':len(selected),'measured_launches':len(measurements),'modes':summary,'kernel_name':name,'grid':[selected[0][1][3],selected[0][1][4]],'threads':128,'registers_per_thread':64,'dynamic_smem':55296}
(a.output/'device-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
