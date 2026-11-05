#!/usr/bin/env python3
"""Render the H20 cache-state investigation from saved, public data."""
from pathlib import Path
import csv
import hashlib
import html
import json
import math
import statistics
import sys
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/h20-tilesight-cache-writeback'
DATA = OUT / 'data'
data = json.loads((DATA / 'measurements.json').read_text())
counters = json.loads((DATA / 'counters.json').read_text())
pred = data['small']['prediction_us']
runs = data['runs']
small = runs['small_default_trace']['modes']
matched = runs['small_matched_trace']['modes']
sweep = runs['small_dirty_footprint_trace']['modes']
clean = small['read_cg512']['median_us']
dirty = small['rmw512']['median_us']
assert math.isclose(pred, 43 * (0.052438813 + 0.882718712) + .587479730 + .043717745 + .220679678, abs_tol=1e-6)
snapshot = json.loads((DATA / 'prediction.json').read_text())
assert math.isclose(dict(snapshot['launches'])['main']['kernel_body_s']*1e6, pred, abs_tol=1e-9)
for run, result in runs.items():
    rows = list(csv.DictReader((DATA / f'{run}.csv').open()))
    assert len(rows) == result['measured_launches']
    for mode, stat in result['modes'].items():
        values = [float(row['device_us']) for row in rows if row['mode'] == mode]
        assert len(values) == stat['samples'] == 51
        assert statistics.median(values) == stat['median_us']

if counters['status'] == 'verified':
    pairs = list(csv.DictReader((DATA / 'counter-dram-pairs.csv').open()))
    assert len(pairs) == 6 and all(int(r['replay_passes']) == 1 for r in pairs)
    deltas = []
    for pair in range(3):
        group = {r['preparation']: r for r in pairs if int(r['pair']) == pair}
        assert set(group) == {'read-only', 'read-modify-write'}
        deltas.append(int(group['read-modify-write']['hbm_write_bytes']) - int(group['read-only']['hbm_write_bytes']))
    assert round(min(deltas)/1e6,2) == 24.04 and round(max(deltas)/1e6,2) == 25.25
    metrics = json.loads((DATA / 'counter-full-metrics.json').read_text())['results']
    for result in metrics.values():
        assert result['profiler__replayer_passes'] == 3
        assert result['smsp__inst_executed_pipe_tensor.sum'] * 4096 == 2 * 16 * 26624 * 2752
        assert result['lts__t_sectors_srcunit_tex_op_write.sum'] * 32 == 16 * 26624 * 2

def esc(x): return html.escape(str(x))
def f(x): return f'{x:.3f}'
labels = [
    ('read_cg512', 'Read-only eviction'),
    ('rmw512', 'Write-based eviction'),
    ('rmw_then_read_cg512', 'Write-based, then read-only eviction'),
    ('rmw_wait200us', 'Write-based, then wait 200 µs'),
    ('rmw_pattern512', 'Write-based, patterned data'),
    ('empty_prep', 'Empty preparation kernel'),
    ('shared_only_prep', 'Shared-memory-only preparation'),
    ('warm', 'Repeated inputs, no eviction'),
]
controls = ''.join(f'<tr><th scope="row">{label}</th><td>{f(small[key]["median_us"])} µs</td><td>{f(matched[key]["median_us"])} µs</td></tr>' for key,label in labels)
sweep_keys = [('ro_then_no_write','None'),('ro_then_empty','Empty kernel'),('ro_then_dirty4mib','4 MiB'),('ro_then_dirty16mib','16 MiB'),('ro_then_dirty32mib','32 MiB'),('ro_then_dirty64mib','64 MiB'),('ro_then_dirty128mib','128 MiB')]
zero = sweep['ro_then_no_write']['median_us']
sweep_rows = ''.join(f'<tr><td>{label}</td><td>{f(sweep[key]["median_us"])} µs</td><td>+{f(sweep[key]["median_us"]-zero)} µs</td></tr>' for key,label in sweep_keys)
baseline = runs['baseline_default_trace']['modes']
scale_rows = ''
for name, shape, modes in [('Original',data['baseline'],baseline),('Reduced',data['small'],small)]:
    ro=modes['read_cg512']['median_us']; rw=modes['rmw512']['median_us']; p=shape['prediction_us']
    scale_rows += f'<tr><th scope="row">{name}</th><td>{shape["n"]:,} / {shape["k"]:,}</td><td>{f(p)}</td><td>{f(rw)}</td><td>{f(ro)}</td><td>{100*(1-p/ro):.2f}%</td></tr>'

if counters['status'] == 'pending':
    counter_html = '<div class="note pending"><strong>Draft: counter verification pending.</strong><p>Controlled timings are complete. Hardware-counter comparisons will be added before publication.</p></div>'
else:
    counter_html = ''.join(f'<p>{esc(p)}</p>' for p in counters.get('paragraphs', []))
    columns = counters.get('columns', [])
    if columns:
        counter_html += '<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th>{esc(c["label"])}</th>' for c in columns) + '</tr></thead><tbody>'
        for row in counters.get('rows', []):
            counter_html += '<tr>'+''.join(f'<td>{esc(row[c["key"]])}</td>' for c in columns)+'</tr>'
        counter_html += '</tbody></table></div>'
    counter_html += ''.join(f'<p class="small">{esc(p)}</p>' for p in counters.get('notes', []))

values = {
    'PRED':f(pred), 'CLEAN':f(clean), 'DIRTY':f(dirty),
    'CLEANERR':f'{100*(1-pred/clean):.2f}', 'DIRTYERR':f'{100*(1-pred/dirty):.2f}',
    'DELTA':f(dirty-clean), 'RESIDUAL':f(clean-pred),
    'REMOVED':f'{100*(dirty-clean)/(dirty-pred):.1f}',
    'CONTROLS':controls, 'SWEEP_ROWS':sweep_rows, 'SCALE_ROWS':scale_rows,
    'COUNTERS':counter_html,
    'COUNTER_STATUS':esc(counters['status']),
}
template = Path(__file__).with_name('template.html').read_text()
for key,value in values.items(): template=template.replace('@@'+key+'@@',value)
assert '@@' not in template
sys.path.insert(0,str(ROOT))
from tools.inject_maas_annotator import expected_text
page=OUT/'index.html'
page.write_text(expected_text(page.resolve(),template))
with ZipFile(OUT/'evidence.zip','w',ZIP_DEFLATED) as bundle:
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and (p.is_relative_to(DATA) or p.is_relative_to(OUT/'source') or p.name=='README.md'):
            bundle.write(p,p.relative_to(OUT))
(OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n' for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
print(f'Rendered {page}; 2,397 device samples verified; counter status={counters["status"]}.')
