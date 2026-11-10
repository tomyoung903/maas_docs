"""Summarize diagnostic CTA thread-0 timestamps, without equating them to Nsight time."""
from pathlib import Path
import argparse, collections, csv, json, statistics

p=argparse.ArgumentParser()
p.add_argument('csv',type=Path)
p.add_argument('--output',type=Path)
a=p.parse_args()
rows=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(a.csv.open())]
assert rows and all(r['entry_ns']<=r['before_mma_ns']<=r['after_mma_ns']<=r['after_epilogue_ns'] for r in rows)
def summary(values):
    x=sorted(v/1000 for v in values)
    return dict(n=len(x),min_us=x[0],p10_us=x[len(x)//10],median_us=statistics.median(x),p90_us=x[len(x)*9//10],max_us=x[-1])
by_sm=collections.defaultdict(list)
for row in rows: by_sm[row['smid']].append(row)
first=min(r['entry_ns'] for r in rows)
last=max(r['after_epilogue_ns'] for r in rows)
result=dict(records=len(rows),sm_count=len(by_sm),ctas_per_sm_histogram=dict(collections.Counter(len(v) for v in by_sm.values())),
            kernel_index=sorted(set(r['gemm_index'] for r in rows)),
            observed_cta_envelope_us=(last-first)/1000,
            entry_spread_us=(max(r['entry_ns'] for r in rows)-first)/1000,
            setup=summary(r['setup_ns'] for r in rows),
            mma_region=summary(r['mma_region_ns'] for r in rows),
            epilogue_region=summary(r['epilogue_region_ns'] for r in rows),
            thread0_total=summary(r['thread0_total_ns'] for r in rows),
            caveats=['Diagnostic instrumented kernel, not the unmodified binary.',
                     'Four timestamp reads are taken only by thread 0; extra registers and final record stores can affect execution.',
                     'MMA region includes operand prefetch, the repeated MMA loop, waits and draining; it is not Tensor Core active time.',
                     'Epilogue region includes output iterator setup, shared-memory reordering, conversions and stores.',
                     'No added barriers; a timestamp does not mean every warp has reached the same point.',
                     'The thread-0 end timestamp precedes diagnostic output stores and kernel completion.'])
if a.output: a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
