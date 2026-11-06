#!/usr/bin/env python3
"""Render the smaller H20 GEMM calculation from recorded TileSight outputs."""
import csv
import hashlib
import html
import json
import math
import statistics
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/h20-tilesight-small-input'
DATA = OUT / 'data'
load = lambda name: json.loads((DATA / name).read_text())
snapshot = load('prediction.json')
plan = load('plan.json')
arch = load('model-provenance.json')['arch']
metadata = load('kernel-metadata.json')
case = load('cases.json')[0]
launch = dict(snapshot['launches'])['main']
region = dict(snapshot['regions'])['main/k']
group = region['groups'][0]
ops = {x['name'].rsplit('/', 1)[-1]: x for x in load('operation-times.json')}
steps = case['k'] // metadata['tile'][2]
ii = group['ii']['selected_ii_s'] * 1e6
offsets = {k: v*1e6 for k,v in group['ii']['witness']}
body = launch['kernel_body_s']*1e6
first = region['first_s']*1e6
steady = region['steady_s']*1e6
drain = region['drain_s']*1e6
assert steps == 43 and launch['physical_ctas'] == 208
assert launch['slots'] == 312 and launch['active_sms'] == 52 and launch['residency'] == 4
assert math.isclose(first+steady+drain, body, abs_tol=1e-10)
assert math.isclose(first, ii, abs_tol=1e-10)
assert math.isclose(steady, (steps-1)*ii, abs_tol=1e-10)
assert math.isclose(drain, sum(ops[n]['us'] for n in ['mma','cast_C','store_C']), abs_tol=1e-10)
assert math.isclose(steps*ii+drain, body, abs_tol=1e-10)
assert abs(ii-ops['load_A']['us']-ops['load_B']['us']) < 1e-7
assert math.isclose(arch['ddr_bandwidth'], load('bandwidth-calibration.json')['selected_bandwidth_Bps'])
assert arch['ddr_max_util'] == 1.0
for op in ops.values():
    assert op['count'] == (208*43 if op['name'].rsplit('/',1)[-1] in ['load_A','load_B','mma'] else 208)

measurements = load('measurements.json')
for name, results in measurements.items():
    rows = list(csv.DictReader((DATA/(name+'.csv')).open()))
    assert len(rows) == 510
    for mode, summary in results['modes'].items():
        times = [float(r['device_us']) for r in rows if r['mode']==mode]
        assert len(times) == summary['samples'] == 51
        assert statistics.median(times) == summary['median_us']
meas = measurements['small_default_trace']['modes']['read_cg512']
dirty = measurements['small_default_trace']['modes']['rmw512']

def timeline(last=False):
    start=(steps-2)*ii if last else 0
    end=body if last else 3*ii+offsets['mma']+ops['mma']['us']
    scale=728/(end-start)
    marks=[]
    for i in range(6):
        x=130+i*728/5; t=start+i*(end-start)/5
        marks.append(f'<path d="M{x:.3f} 20 V259" stroke="#d9e3e8"/><text x="{x:.3f}" y="280" text-anchor="middle">{t:.2f}</text>')
    def bar(name,label,t,y,color):
        dt=ops[name]['us']; x=130+(t-start)*scale; w=dt*scale
        marks.append(f'<rect x="{x:.3f}" y="{y}" width="{w:.3f}" height="32" rx="3" fill="{color}"><title>{label}: {t:.9f}–{t+dt:.9f} µs</title></rect>')
        if w>43:marks.append(f'<text x="{x+w/2:.3f}" y="{y+21}" text-anchor="middle" fill="white">{label}</text>')
    for k in (range(steps-2,steps) if last else range(4)):
        for name,label,y,color in [('load_A','A',35,'#407eaa'),('load_B','B',94,'#96602a'),('mma','MMA',153,'#146b67')]:
            bar(name,f'{label} {k}',k*ii+offsets[name],y,color)
    if last:
        t=(steps-1)*ii+offsets['mma']+ops['mma']['us']
        for name,label in [('cast_C','cast'),('store_C','store')]:
            bar(name,label,t,212,'#7956a4');t+=ops[name]['us']
        assert math.isclose(t,body,abs_tol=1e-9)
    for label,y in [('Load A',56),('Load B',115),('Tensor MMA',174),('Output',233)]:
        marks.append(f'<text x="4" y="{y}">{label}</text>')
    return '<svg viewBox="0 0 890 305" role="img" aria-label="Saved modeled operation schedule"><title>TileSight schedule, not a measured internal trace</title>'+''.join(marks)+'<text x="860" y="302">µs</text></svg>'

def grid_svg():
    marks=[]
    for sm in range(78):
        x=8+(sm%13)*66; y=8+(sm//13)*65
        marks.append(f'<g><title>Illustrative model SM {sm}: '+('four occupied slots' if sm<52 else 'four unoccupied slots')+'</title>')
        marks.append(f'<rect x="{x}" y="{y}" width="60" height="58" rx="5" fill="#f4f8f8" stroke="#d5e1e4"/><text x="{x+30}" y="{y+16}" text-anchor="middle" style="font-size:12px">SM {sm}</text>')
        for slot in range(4):
            color='#146b67' if sm<52 else '#dde5e9'
            marks.append(f'<rect x="{x+7+(slot%2)*25}" y="{y+23+(slot//2)*15}" width="21" height="11" rx="2" fill="{color}"/>')
        marks.append('</g>')
    return '<svg viewBox="0 0 874 405" role="img" aria-label="Illustrative model packing: 52 groups of four occupied CTA slots and 26 unoccupied groups"><title>52 modeled active SMs, not measured physical placement</title>'+''.join(marks)+'</svg>'

resources=['ddr','l2','smem','cp_async','tensor','cuda','register','ldst']
rows=''
for name,o in ops.items():
    row=''.join(f'<td>{o["resources_us"][r]:.6f}</td>' if r in o['resources_us'] else '<td>—</td>' for r in resources)
    rows+=f'<tr><th><code>{name}</code></th>{row}<td><b>{o["us"]:.6f}</b></td></tr>'

M,N,K=case['m'],case['n'],case['k']
flops=2*M*N*K
traffic=2*(M*K+K*N+M*N)
numbers={**case,'sm_count':78,'residency':4,'slots':312,'active_sms':52,'concurrent_ctas':208,
         'waves':1,'steps':steps,'ii_us':ii,'offsets_us':offsets,'first_us':first,'steady_us':steady,
         'drain_us':drain,'prediction_us':body,'read_only_us':meas['median_us'],'write_based_us':dirty['median_us'],
         'ops':ops,'flops':flops,'ideal_bytes':traffic,'arithmetic_intensity':flops/traffic,
         'hbm_bps':arch['ddr_bandwidth'],'hbm_share_bps':arch['ddr_bandwidth']/208,
         'l2_share_bps':arch['l2_bandwidth']/208,'smem_share_bps':arch['smem_bandwidth']/312,
         'tensor_share_flops':arch['fp16_tensor_flops']/312}
(DATA/'numbers.json').write_text(json.dumps(numbers,indent=2)+'\n')
recipe=(OUT/'source/predict.py').read_text()
recipe=recipe[recipe.index('    kb=KernelBuilder'):recipe.index("    (dest/'plan.json')")]
recipe='\n'.join(x[4:] if x.startswith('    ') else x for x in recipe.splitlines())
repl={
 'NAV':''.join(f'<a href="#{a}">{b}</a>' for a,b in [('setup','1 · Choose the workload'),('tiles','2 · Divide the work'),('plan','3 · Describe one tile'),('costs','4 · Price the operations'),('overlap','5 · Overlap the K steps'),('grid','6 · Schedule the grid'),('result','7 · Compare with measurement'),('source','Code and saved data')]),
 'ROWS':rows,'FIRST':timeline(),'LAST':timeline(True),'GRID':grid_svg(),'RECIPE':html.escape(recipe),
 'PRED':f'{body:.3f}','MEAS':f'{meas["median_us"]:.3f}','DIRTY':f'{dirty["median_us"]:.3f}',
 'ERROR':f'{100*(1-body/meas["median_us"]):.2f}','DIRTYERROR':f'{100*(1-body/dirty["median_us"]):.2f}',
 'BW':f'{arch["ddr_bandwidth"]/1e12:.9f}','HBMSHARE':f'{arch["ddr_bandwidth"]/208/1e9:.6f}',
 'L2SHARE':f'{arch["l2_bandwidth"]/208/1e9:.6f}',
 'AI':f'{flops/traffic:.4f}','COMPUTELOWER':f'{flops/arch["fp16_tensor_flops"]*1e6:.3f}',
 'MEMLOWER':f'{traffic/arch["ddr_bandwidth"]*1e6:.3f}',
 'II':f'{ii:.9f}','A':f'{ops["load_A"]["us"]:.9f}','B':f'{ops["load_B"]["us"]:.9f}',
 'MMA':f'{ops["mma"]["us"]:.9f}','CAST':f'{ops["cast_C"]["us"]:.9f}',
 'STORE':f'{ops["store_C"]["us"]:.9f}','BODY':f'{body:.9f}',
 'FIRSTUS':f'{first:.9f}','STEADYUS':f'{steady:.9f}','DRAINUS':f'{drain:.9f}',
 'RESOURCEII':f'{group["ii"]["resource_ii_s"]*1e6:.9f}',
 'BSTART':f'{offsets["load_B"]:.9f}','MMASTART':f'{offsets["mma"]:.9f}',
 'P10':f'{meas["p10_us"]:.3f}','P90':f'{meas["p90_us"]:.3f}',
 'GAP':f'{meas["median_us"]-body:.6f}',
 'TFLOPS':f'{flops/(meas["median_us"]*1e-6)/1e12:.4f}',
 'FLOPSUTIL':f'{flops/(meas["median_us"]*1e-6)/148e12*100:.2f}',
 'USEFULBW':f'{2*N*K/(meas["median_us"]*1e-6)/1e12:.6f}',
 'BWUTIL':f'{2*N*K/(meas["median_us"]*1e-6)/arch["ddr_bandwidth"]*100:.2f}',
}
text=Path(__file__).with_name('template.html').read_text()
for key,value in repl.items():text=text.replace('@@'+key+'@@',value)
assert '@@' not in text
sys.path.insert(0,str(ROOT))
from tools.inject_maas_annotator import expected_text
page=OUT/'index.html';page.write_text(expected_text(page.resolve(),text))
with ZipFile(OUT/'evidence.zip','w',ZIP_DEFLATED) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and (p.is_relative_to(DATA) or p.is_relative_to(OUT/'source') or p.name=='README.md'):
            z.write(p,p.relative_to(OUT))
(OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n' for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
print(f'Rendered {page}: {body:.9f} µs vs {meas["median_us"]:.3f} µs; 1,020 samples and model arithmetic verified.')
