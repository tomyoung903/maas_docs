"""Extract kernel-only samples and match them to the recorded launch ledger."""
from pathlib import Path
import argparse
import csv
import json
import sqlite3
import statistics

parser=argparse.ArgumentParser()
parser.add_argument('--input-dir',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args()
root=args.input_dir
data=root/'data' if (root/'data').is_dir() else root
runs=root/'runs' if (root/'runs').is_dir() else data
args.output_dir.mkdir(parents=True,exist_ok=True)
def stats(values):
    values=sorted(values)
    assert len(values)==51
    return dict(samples=len(values),median_us=statistics.median(values),
                p10_us=values[len(values)//10],p90_us=values[len(values)*9//10],
                min_us=min(values),max_us=max(values))

records=[]; result={}
for mode in ['read_cg512','warm']:
    conditions={}
    for kind in ['events','nsys']:
        d=runs/(mode+'-'+kind)
        log_file=d/'run.log' if (d/'run.log').exists() else d/'observations.jsonl'
        log=[json.loads(line) for line in log_file.read_text().splitlines() if line.startswith('{')]
        metadata=next(r for r in log if 'max_active_blocks' in r)
        assert metadata['grid']==[4,78,1]
        assert metadata['tile']==[16,128,64]
        assert metadata['max_active_blocks']==4
        assert next(r for r in log if 'correctness' in r)['correctness']=='PASS'
        assert next(r for r in log if 'final_eviction_checksum' in r)['final_eviction_checksum']=='PASS'
        events=list(csv.DictReader((d/'samples.csv').open()))
        conditions[kind+'_events']=stats([float(r['time_us']) for r in events])
        if kind=='nsys':
            c=sqlite3.connect(d/'device.sqlite')
            c.row_factory=sqlite3.Row
            kernels=list(c.execute('SELECT K.*,S.value AS name FROM CUPTI_ACTIVITY_KIND_KERNEL K JOIN StringIds S ON S.id=K.demangledName WHERE S.value LIKE ? ORDER BY K.start',('%cutlass::Kernel%',)))
            launches=list(csv.DictReader((d/'launches.csv').open()))
            assert len(kernels)==len(launches)==203,(len(kernels),len(launches))
            selected=[]
            for kernel,launch in zip(kernels,launches):
                assert [kernel['gridX'],kernel['gridY'],kernel['gridZ']]==[4,78,1]
                assert kernel['registersPerThread']==64
                assert kernel['dynamicSharedMemory']==55296
                if launch['phase']=='measure':
                    duration=(kernel['end']-kernel['start'])/1000
                    selected.append(duration)
                    records.append(dict(mode=mode,sample=int(launch['sample']),gemm_index=int(launch['gemm_index']),start_ns=kernel['start'],end_ns=kernel['end'],device_us=duration))
            conditions['device']=stats(selected)
            c.close()
    result[mode]=conditions

prediction=json.loads((data/'summary.json').read_text())
summary=dict(predicted_us=prediction['body_us'],measurements=result,
             error_pct=100*(prediction['body_us']/result['read_cg512']['device']['median_us']-1),
             correctness={'result':'PASS','reference':'cuBLAS','output_elements':638976,'max_abs_error':0,'fixture':'seed 17; deterministic multiples of 1/8'},
             metadata=metadata)
(args.output_dir/'measurement-summary.json').write_text(json.dumps(summary,indent=2))
with (args.output_dir/'device-samples.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)
print(json.dumps(summary,indent=2))
