#!/usr/bin/env python3
"""Render the memory-bound walkthrough from the archived experiment snapshots."""
import hashlib
import html
import json
import math
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/h20-tilesight-memory-bound'
DATA = OUT / 'data'
load = lambda name: json.loads((DATA / name).read_text())
case = load('comparison.json')['cases'][0]
ops = {o['name'].rsplit('/', 1)[-1]: o for o in load('operation-times.json')}
snapshot = load('prediction.json')
region = dict(snapshot['regions'])['main/k']
group = region['groups'][0]
ii = group['ii']['selected_ii_s'] * 1e6
offsets = {k: v * 1e6 for k, v in group['ii']['witness']}
tile_us = region['total_s'] * 1e6
arch = load('model-provenance.json')['arch']
meta = load('kernel-metadata.json')
slots = arch['sm_count'] * meta['max_active_blocks']
steps = case['k'] // meta['tile'][2]
parts = steps * ii + sum(ops[n]['us'] for n in ['load_A', 'mma', 'cast_C', 'store_C'])
assert math.isclose(parts, tile_us, rel_tol=1e-10)
assert math.isclose(case['waves'] * tile_us, case['predicted_us'], rel_tol=1e-10)
assert slots * case['waves'] == case['ctas']

def timeline(last=False):
    start = (steps-2) * ii if last else 0
    end = tile_us if last else 3*ii + offsets['mma'] + ops['mma']['us']
    left, right = 130, 858
    scale = (right-left)/(end-start)
    bars, ticks = [], []
    for i in range(6):
        x = left+(right-left)*i/5
        t = start+(end-start)*i/5
        ticks.append(f'<path d="M{x:.3f},20 V259" stroke="#d9e3e8"/><text x="{x:.3f}" y="280" text-anchor="middle">{t:.2f}</text>')
    def bar(name, label, t, y, color):
        duration = ops[name]['us']
        x, w = left+(t-start)*scale, duration*scale
        bars.append(f'<rect x="{x:.3f}" y="{y}" width="{w:.3f}" height="32" rx="3" fill="{color}"><title>{label}: {t:.6f}–{t+duration:.6f} µs</title></rect>')
        if w>43:
            bars.append(f'<text x="{x+w/2:.3f}" y="{y+21}" text-anchor="middle" fill="white">{label}</text>')
    for k in (range(steps-2,steps) if last else range(4)):
        for name, y, color, label in [('load_A',35,'#407eaa','A'),('load_B',94,'#96602a','B'),('mma',153,'#146b67','MMA')]:
            bar(name,f'{label} {k}',k*ii+offsets[name],y,color)
    if last:
        t = (steps-1)*ii + offsets['mma'] + ops['mma']['us']
        for name, label in [('cast_C','cast'),('store_C','store')]:
            bar(name,label,t,212,'#7956a4');t += ops[name]['us']
        assert math.isclose(t,tile_us,rel_tol=1e-10)
    labels = ''.join(f'<text x="4" y="{y}">{label}</text>' for y,label in [(56,'Load A'),(115,'Load B'),(174,'Tensor MMA'),(233,'Output')])
    return f'<svg viewBox="0 0 890 305" role="img" aria-label="Modeled operation timeline: {"last two" if last else "first four"} K steps"><title>TileSight periodic schedule, not a measured GPU trace</title>{"".join(ticks)}{labels}{"".join(bars)}<text x="860" y="302">µs</text></svg>'

resources = ['ddr','l2','smem','cp_async','tensor','cuda','register','ldst']
rows = ''
for name,o in ops.items():
    values = ''.join(f'<td>{o["resources_us"][r]:.6f}</td>' if r in o['resources_us'] else '<td>—</td>' for r in resources)
    rows += f'<tr><th scope="row"><code>{name}</code></th>{values}<td><b>{o["us"]:.6f}</b></td></tr>'
toc = [('setup','1 · Choose the workload'),('tiles','2 · Divide the work'),('plan','3 · Describe one tile'),('costs','4 · Price the operations'),('overlap','5 · Overlap the K steps'),('grid','6 · Schedule the grid'),('result','7 · Compare with measurement'),('source','Code and saved data')]
numbers = dict(case, slots=slots, k_steps=steps, tile_us=tile_us, ii_us=ii, offsets_us=offsets,
               ops=ops, flops=2*case['m']*case['n']*case['k'])
numbers['ideal_bytes'] = 2*(case['m']*case['k']+case['k']*case['n']+case['m']*case['n'])
numbers['ai'] = numbers['flops']/numbers['ideal_bytes']
(DATA/'numbers.json').write_text(json.dumps(numbers,indent=2)+'\n')
recipe = (OUT/'source/predict.py').read_text()
recipe = recipe[recipe.index("    kb=KernelBuilder"):recipe.index("    (dest/'plan.json')")]
recipe = '\n'.join(line[4:] if line.startswith('    ') else line for line in recipe.splitlines())
replace = {
    'NAV': ''.join(f'<a href="#{key}">{label}</a>' for key,label in toc),
    'ROWS':rows,'FIRST':timeline(),'LAST':timeline(True),'RECIPE':html.escape(recipe),
    'PRED':f'{case["predicted_us"]:.2f}','MEAS':f'{case["device_cold_us"]:.2f}',
    'ERROR':f'{abs(case["error_pct"]):.2f}','TILE':f'{tile_us:.9f}',
}
page = Path(__file__).with_name('template.html').read_text()
for key,value in replace.items():page=page.replace('@@'+key+'@@',value)
assert '@@' not in page
sys.path.insert(0,str(ROOT))
from tools.inject_maas_annotator import expected_text
path=OUT/'index.html'
path.write_text(expected_text(path.resolve(),page))
with ZipFile(OUT/'evidence.zip','w',ZIP_DEFLATED) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and (p.is_relative_to(DATA) or p.is_relative_to(OUT/'source') or p.name=='README.md'):
            z.write(p,p.relative_to(OUT))
manifest=''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n' for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS')
(OUT/'SHA256SUMS').write_text(manifest)
print(f'Rendered {path}: {case["predicted_us"]:.9f} µs; arithmetic checks passed.')
