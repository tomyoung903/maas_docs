"""Publish the fixed L2-bound candidate and its independently measured result."""
import hashlib
import html
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.h20_gemm_utilization import utilization_section
from tools.inject_maas_annotator import expected_text
from tools.h20_tilesight_l2_bound.investigation import render as render_investigation
OUT=ROOT/'docs/h20-tilesight-l2-bound'
load=lambda name:json.loads((OUT/'data'/name).read_text())
model=load('summary.json'); measured=load('measurement-summary.json'); snapshot=load('prediction.json')
counters=load('counter-summary.json')
ops={r['name'].rsplit('/',1)[-1]:r for r in model['ops']}
region=dict(snapshot['regions'])['main/k']
ii=region['ii']['selected_ii_s']*1e6
offsets=dict(region['ii']['witness'])
assert model['shape_mnk']==[64,9984,2048] and model['grid']==[4,78]
assert abs(ii-sum(ops[n]['resources_us']['l2'] for n in ['load_A','load_B']))<1e-12
assert abs(model['body_us']-32*ii-sum(ops[n]['completion_us'] for n in ['mma','cast_C','store_C']))<1e-10
cold=measured['measurements']['read_cg512']['device']
warm=measured['measurements']['warm']['device']
assert cold['samples']==warm['samples']==51
assert measured['correctness']['result']=='PASS'
full=counters['cold-full2/verified-report'];cold_bytes=counters['cold-traffic'];warm_bytes=counters['warm-traffic']
assert full['smsp__inst_executed_pipe_tensor.sum']*4096==model['flops']

def timeline(last=False):
    start=30*ii if last else 0
    end=model['body_us'] if last else 3*ii+ops['mma']['completion_us']
    left,right=126,850;scale=(right-left)/(end-start)
    marks=[]
    for j in range(6):
        t=start+(end-start)*j/5;x=left+(right-left)*j/5
        marks.append(f'<line x1="{x}" x2="{x}" y1="18" y2="239" stroke="#d9e3e8"/><text x="{x}" y="264" text-anchor="middle">{t:.2f}</text>')
    for k in (range(30,32) if last else range(3)):
        for name,y,color,label in [('load_A',30,'#397ca2','A'),('load_B',82,'#b3722c','B'),('mma',134,'#146b67','MMA')]:
            t=k*ii+offsets[name]*1e6;x=left+(t-start)*scale;w=ops[name]['completion_us']*scale
            marks.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="3" fill="{color}"><title>{label} {k}: {t:.6f}–{t+ops[name]["completion_us"]:.6f} µs</title></rect>')
    if last:
        t=32*ii+ops['mma']['completion_us']
        for name in ['cast_C','store_C']:
            x=left+(t-start)*scale;w=ops[name]['completion_us']*scale
            marks.append(f'<rect x="{x}" y="186" width="{w}" height="30" rx="3" fill="#78599c"><title>{name}: {t:.6f}–{t+ops[name]["completion_us"]:.6f} µs</title></rect>')
            t+=ops[name]['completion_us']
    for y,label in [(50,'Load A'),(102,'Load B'),(154,'Tensor MMA'),(206,'Output')]:
        marks.append(f'<text x="4" y="{y}">{label}</text>')
    return '<svg viewBox="0 0 880 290" role="img" aria-label="Modeled operation schedule, not measured internal stage durations">'+''.join(marks)+'<text x="838" y="286">µs</text></svg>'

def fmt(x):return f'{x:,.0f}'
def resource_rows():
    result=[]
    for name,op in ops.items():
        cells=''.join(f'<td>{op["resources_us"][r]:.6f}</td>' if r in op['resources_us'] else '<td>—</td>' for r in ['ddr','l2','smem','tensor','cuda'])
        result.append(f'<tr><th><code>{name}</code></th>{cells}<td>{op["completion_us"]:.6f}</td></tr>')
    return ''.join(result)

toc=[('investigation','Follow-up · Explain the gap'),('setup','1 · The candidate'),('grid','2 · Divide the work'),('cache','3 · Reuse the inputs'),('costs','4 · Resource costs'),('overlap','5 · Model the pipeline'),('result','6 · Measure the kernel'),('counters','7 · Inspect counters'),('source','Evidence and limits'),('utilization','Utilization rates')]
data=dict(NAV=''.join(f'<a href="#{i}">{t}</a>' for i,t in toc),PRED=f'{model["body_us"]:.3f}',MEAS=f'{cold["median_us"]:.3f}',ERROR=f'{abs(measured["error_pct"]):.2f}',GAP=f'{cold["median_us"]-model["body_us"]:.3f}',
          WARM=f'{warm["median_us"]:.3f}',P10=f'{cold["p10_us"]:.3f}',P90=f'{cold["p90_us"]:.3f}',
          EVENT=f'{measured["measurements"]["read_cg512"]["events_events"]["median_us"]:.3f}',
          II=f'{ii:.9f}',FIRST=timeline(),LAST=timeline(True),ROWS=resource_rows(),
          HBMLIMIT=f'{sum(model[n] for n in ["A_bytes","B_bytes","C_bytes"])/model["arch"]["ddr_bandwidth"]*1e6:.3f}',
          L2LIMIT=f'{model["l2_read_bytes"]/model["arch"]["l2_bandwidth"]*1e6:.3f}',
          COMPUTELIMIT=f'{model["flops"]/model["arch"]["fp16_tensor_flops"]*1e6:.3f}',
          COLDREAD=fmt(cold_bytes['dram__bytes_read.sum']),WARMREAD=fmt(warm_bytes['dram__bytes_read.sum']),
          COLDWRITE=fmt(cold_bytes['dram__bytes_write.sum']),WARMWRITE=fmt(warm_bytes['dram__bytes_write.sum']),
          COLDL2=fmt(32*cold_bytes['lts__t_sectors_op_read.sum']),WARML2=fmt(32*warm_bytes['lts__t_sectors_op_read.sum']),
          L2ACTIVE=f'{full["lts__throughput.avg.pct_of_peak_sustained_elapsed"]:.2f}',
          DRAMACTIVE=f'{full["dram__throughput.avg.pct_of_peak_sustained_elapsed"]:.2f}',
          TENSORACTIVE=f'{full["sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_elapsed"]:.2f}',
          NCUTIME=f'{full["gpu__time_duration.sum"]/1000:.3f}',
          NCUL2=fmt(32*full['lts__t_sectors_op_read.sum']),TENSORINST=fmt(full['smsp__inst_executed_pipe_tensor.sum']),
          REDUCTION=f'{100*(1-warm_bytes["dram__bytes_read.sum"]/cold_bytes["dram__bytes_read.sum"]):.2f}',
          WARMDELTA=f'{cold["median_us"]-warm["median_us"]:.3f}',
          DOUBLING=''.join(f'<tr><td>{html.escape(label)}</td><td>{model["rate_sensitivity"][key]:.3f} µs</td></tr>' for key,label in [('l2_bandwidth_doubled','Double only L2 bandwidth'),('ddr_bandwidth_doubled','Double only HBM bandwidth'),('fp16_tensor_flops_doubled','Double only Tensor throughput')]))
page=Path(__file__).with_name('template.html').read_text()
page=page.replace('@@INVESTIGATION@@',render_investigation(OUT))
for key,value in data.items():page=page.replace('@@'+key+'@@',value)
utilization=utilization_section(OUT,model['shape_mnk'],cold['median_us'],'read-only cache eviction')
page=page.replace('@@UTILIZATION@@',utilization.replace('<h2>8. FLOP and bandwidth utilization</h2>', '<h2>9. FLOP and bandwidth utilization</h2>'))
assert '@@' not in page
path=OUT/'index.html';path.write_text(expected_text(path.resolve(),page))
with ZipFile(OUT/'evidence.zip','w',ZIP_DEFLATED) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and (p.is_relative_to(OUT/'data') or p.is_relative_to(OUT/'source') or p.name=='README.md'):
            z.write(p,p.relative_to(OUT))
(OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n' for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
print(f'Rendered {path}: {model["body_us"]:.6f} µs predicted, {cold["median_us"]:.3f} µs measured.')
