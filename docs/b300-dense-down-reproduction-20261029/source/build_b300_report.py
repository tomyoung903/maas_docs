#!/usr/bin/env python3
"""Publishable, offline B300 dense-down report from measured Nsight results.

Input: a row list, or {"rows": [...], "metadata": {...}}.  Metrics are GPU
active-union median and per-kernel means, in microseconds.  No missing metric is
estimated.  This tool does not label CUDA-event timings as active GPU time.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
import shutil
import statistics
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASELINE = Path(__file__).with_name('reference.json')
if not BASELINE.exists():
    BASELINE = Path('/home/tom/maas_docs/docs/tmp/glm52-gb300-dense-down-kernel-tutorial/sweep-data.js')
BASE_URL = 'https://tomyoung903.github.io/maas_docs/tmp/glm52-gb300-dense-down-kernel-tutorial/'


def first(d, keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def normalized(payload):
    meta = {}
    if isinstance(payload, dict):
        meta = payload.get('metadata', payload.get('run_metadata', payload.get('environment', {})))
        rows = first(payload, ('rows', 'points', 'results', 'measurements'))
        if rows is None:
            raise ValueError('Input object requires rows, points, results or measurements')
    else:
        rows = payload
    if not isinstance(rows, list) or not rows:
        raise ValueError('No measured rows; refusing to generate a B300 result')
    result = []
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError('Every measured row must be an object')
        raw_samples = raw.get('samples')
        count = first(raw, ('sample_count', 'repeats'))
        if count is None:
            count = len(raw_samples) if isinstance(raw_samples, list) else raw_samples
        row = {
            'm': int(first(raw, ('m', 'M', 'batch_size', 'batch'))),
            'n': int(first(raw, ('n', 'N'), 6144)),
            'k': int(first(raw, ('k', 'K'), 1536)),
            'active_union_median_us': float(first(raw, ('active_union_median_us', 'active_union_us', 'median_us', 'total_median_us'))),
            'quant_mean_us': float(first(raw, ('quant_mean_us', 'quant_us', 'quantization_mean_us'))),
            'gemm_mean_us': float(first(raw, ('gemm_mean_us', 'gemm_us'))),
            'samples': int(count or 0),
        }
        if row['n'] != 6144 or row['k'] != 1536:
            raise ValueError(f'Unexpected matrix shape at M={row["m"]}: N/K must be 6144/1536')
        if row['m'] <= 0 or row['samples'] <= 0:
            raise ValueError(f'Invalid M or sample count: {row}')
        for key in ('active_union_median_us', 'quant_mean_us', 'gemm_mean_us'):
            if not math.isfinite(row[key]) or row[key] <= 0:
                raise ValueError(f'Invalid measured {key} at M={row["m"]}')
        for key in ('kernel_name', 'quant_kernel_name', 'block_m', 'stages', 'kernel_count', 'sample_kernel_count_min', 'sample_kernel_count_max'):
            if key in raw:
                row[key] = raw[key]
        if isinstance(raw_samples, list):
            if len(raw_samples) != row['samples']:
                raise ValueError(f'Sample count disagrees with retained samples at M={row["m"]}')
            row['sample_evidence'] = raw_samples
        result.append(row)
    result.sort(key=lambda r: r['m'])
    if len({r['m'] for r in result}) != len(result):
        raise ValueError('Duplicate M rows; aggregate explicit repeated runs before publishing')
    meta = dict(meta) if isinstance(meta, dict) else {'description': str(meta)}
    if isinstance(payload, dict):
        for key in ('nvtx_range_count', 'valid_sample_count', 'measurement'):
            if key in payload:
                meta[key] = payload[key]
        if 'rejected_samples' in payload:
            meta['rejected_sample_count'] = len(payload['rejected_samples'])
    return result, meta


def baseline_rows(path):
    if path.suffix == '.json':
        data = json.loads(path.read_text())
        return data['rows'] if isinstance(data, dict) else data
    text = path.read_text()
    marker = re.search(r'rows:\s*\[', text)
    if not marker:
        raise ValueError('Cannot find original reference rows')
    start = text.index('[', marker.start())
    depth = 0
    end = None
    for index in range(start, len(text)):
        if text[index] == '[':
            depth += 1
        elif text[index] == ']':
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise ValueError('Unterminated reference array')
    array = json.loads(re.sub(r',\s*]', ']', text[start:end]))
    rows = []
    for a in array:
        rows.append({'m': int(a[0]), 'active_union_median_us': a[1], 'quant_mean_us': a[2], 'gemm_mean_us': a[3], 'block_m': a[4], 'stages': a[5], 'samples': a[9]})
    if not rows:
        raise ValueError('No original reference points were parsed')
    return rows


def clean_metadata(meta):
    # Explicit allowlist keeps access details and private paths out of public docs.
    aliases = {'device_name':'gpu_name','torch_cuda':'cuda','deep_gemm_version':'deepgemm_package_version','quant_identity':'quant_source_identity','measurement':'metric','input_model':'input_policy'}
    expanded = {aliases.get(k,k):v for k,v in meta.items()}
    expanded.setdefault('deepgemm_commit','b4296edce3cd07e3b6392c8eb390cee9c41a6b70')
    if 'cpu_architecture' not in expanded and isinstance(meta.get('platform'),str):
        for arch in ('x86_64','aarch64','arm64'):
            if arch in meta['platform']:
                expanded['cpu_architecture'] = arch
                break
    for src,dest in [('started_epoch','started_at'),('completed_epoch','completed_at'),('finished_epoch','completed_at')]:
        if src in meta and dest not in expanded:
            expanded[dest] = datetime.fromtimestamp(meta[src],timezone.utc).isoformat(timespec='seconds')
    allowed = ('gpu', 'gpu_name', 'sm_count', 'compute_capability', 'cpu_architecture', 'architecture', 'torch', 'torch_version', 'cuda', 'cuda_version', 'driver', 'driver_version', 'nvcc', 'nsys', 'nsys_version', 'triton', 'deepgemm', 'deepgemm_commit', 'deepgemm_version', 'deepgemm_package_version', 'quant_source_sha256', 'quant_source_revision', 'quant_source_match', 'quant_source_identity', 'source_hashes', 'warmups', 'repeats', 'samples_per_shape', 'seed', 'timing_mode', 'metric', 'input_policy', 'correctness', 'validation', 'status', 'power_limit_w', 'clock_policy', 'started_at', 'completed_at', 'timestamp_utc', 'limitations', 'notes', 'kernel_count_validation', 'input_dtype', 'output_dtype', 'weight_dtype', 'scale_dtype', 'scale_block', 'cuda_graphs', 'l2_flush', 'source_identity', 'nvtx_range_count', 'valid_sample_count', 'rejected_sample_count')
    extra = ('warmup_policy', 'benchmark_source_sha256')
    return {k: expanded[k] for k in allowed + extra if k in expanded}


def plots(rows, baseline, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'svg.fonttype':'none', 'axes.spines.top':False, 'axes.spines.right':False})
    fig, ax = plt.subplots(figsize=(11.6, 4.5), layout='constrained')
    x = [r['m'] for r in rows]
    ax.plot([r['m'] for r in baseline], [r['active_union_median_us'] for r in baseline], color='#8894a2', linestyle='--', linewidth=1.6, label='GB300 reference · active union')
    for key, label, color, width in [('active_union_median_us','B300 · active union','#13786f',2.2),('gemm_mean_us','B300 · GEMM mean','#3967ce',1.7),('quant_mean_us','B300 · quantization mean','#c97526',1.7)]:
        ax.plot(x, [r[key] for r in rows], label=label, color=color, linewidth=width)
    ax.set_xscale('log')
    ax.set_xlim(min(min(x),1),max(max(x),10000))
    ax.set_ylim(bottom=0)
    ax.set_xlabel('M · input rows (logarithmic axis)')
    ax.set_ylabel('GPU kernel time (µs)')
    ax.set_title('Dense down projection · N = 6144, K = 1536', loc='left', fontsize=13, fontweight='bold', pad=12)
    ax.grid(axis='y', color='#e4e8ed', linewidth=.8)
    ax.legend(loc='upper left', frameon=False, fontsize=9)
    for ext in ('svg','png'):
        fig.savefig(output / f'kernel-time.{ext}', dpi=180, facecolor='white')
    plt.close(fig)


CSS = '''
:root{--ink:#182b39;--muted:#607180;--line:#dfe6e8;--paper:#f3f6f5;--teal:#13786f;--blue:#3967ce;--orange:#c97526}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:#116b68;text-underline-offset:3px}header{background:#102c36;color:#fff;padding:37px 0 31px}.wrap{width:min(1240px,calc(100% - 80px));margin:auto}header a{color:#b7ddd7}.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;font-weight:700;color:#89c9bb;margin:0 0 12px}h1{font-size:40px;letter-spacing:-.045em;line-height:1.15;margin:0 0 15px}header p{max-width:880px;color:#cddce0;margin:0 0 12px}h2{font-size:23px;letter-spacing:-.025em;margin:0 0 8px}h3{font-size:16px;margin:0 0 7px}p{margin:0 0 12px}.muted{color:var(--muted)}main{padding:25px 0 50px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:23px}.card,.panel{background:white;border:1px solid var(--line);border-radius:13px}.card{padding:18px}.card strong{font-size:26px;letter-spacing:-.04em;display:block}.card span,.card small{display:block;color:var(--muted)}.card span{font-size:12px;font-weight:650;text-transform:uppercase;letter-spacing:.07em}.card small{font-size:12px}.panel{padding:25px;margin:0 0 20px}.panel-head{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}.panel-head p{max-width:850px}.tag{display:inline-block;color:#11655d;background:#e5f3ee;border-radius:99px;padding:5px 11px;font-size:12px;white-space:nowrap;font-weight:700}.chart{width:100%;display:block}.downloads{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px;font-size:13px}.two{display:grid;grid-template-columns:1.25fr 1fr;gap:20px}.two>.panel{height:100%}.spec{display:grid;grid-template-columns:130px 1fr;gap:9px 16px;margin:17px 0 0}.spec dt{color:var(--muted)}.spec dd{margin:0;word-break:break-word}code{font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;background:#eef3f3;border-radius:4px;padding:2px 4px;overflow-wrap:anywhere}.notice{border-left:4px solid #d7a45a;padding:11px 15px;background:#fff8ec;border-radius:0 7px 7px 0;font-size:13px;margin-top:16px}.table-scroll{overflow:auto;max-height:620px}table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}th,td{text-align:right;padding:10px 12px;border-bottom:1px solid #e5ebed}th:first-child,td:first-child{text-align:left}th{background:#f5f8f8;color:#56707b;position:sticky;top:0;font-weight:650}tbody tr:hover{background:#f1f7f5}summary{cursor:pointer;font-weight:700}details{margin-top:18px}footer{color:var(--muted);font-size:12px;margin-top:25px}.meta{display:grid;grid-template-columns:200px 1fr;gap:6px 18px;font-size:13px;margin:15px 0 0}.meta dt{color:var(--muted)}.meta dd{margin:0;overflow-wrap:anywhere}.small{font-size:13px}.anchors{margin-top:19px}.check{color:#0b7862;font-weight:700}.unverified{color:#8a651e;font-weight:700}
'''


def esc(v):
    return html.escape(str(v))


def row_html(rows, base):
    out = []
    for r in rows:
        b = base.get(r['m'])
        ref = f'{b["active_union_median_us"]:.3f}' if b else '—'
        ratio = f'{r["active_union_median_us"]/b["active_union_median_us"]:.3f}×' if b else '—'
        out.append(f'<tr><td>{r["m"]:,}</td><td>{r["active_union_median_us"]:.3f}</td><td>{r["quant_mean_us"]:.3f}</td><td>{r["gemm_mean_us"]:.3f}</td><td>{ref}</td><td>{ratio}</td><td>{r["samples"]}</td></tr>')
    return '\n'.join(out)


def render(rows, baseline, meta, output, sources):
    output.mkdir(parents=True, exist_ok=True)
    cleaned = clean_metadata(meta)
    base = {r['m']:r for r in baseline}
    total_samples = sum(r['samples'] for r in rows)
    comparison = [r['active_union_median_us']/base[r['m']]['active_union_median_us'] for r in rows if r['m'] in base]
    ratio = statistics.median(comparison) if comparison else None
    ratio_text = f'{ratio:.3f}×' if ratio else '—'
    all_data = {'schema_version':'b300-dense-down-reproduction-v1','metric':'Nsight GPU-active interval union; not CUDA-event elapsed time','metadata':cleaned,'rows':rows,'reference':{'url':BASE_URL,'date':'2026-08-19','hardware':'GB300','rows':baseline}}
    (output/'results.json').write_text(json.dumps(all_data,indent=2)+'\n')
    fields = ['m','n','k','active_union_median_us','quant_mean_us','gemm_mean_us','samples','gb300_reference_active_union_us','b300_over_gb300']
    with (output/'results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:
            b=base.get(r['m']); d={k:r[k] for k in fields if k in r}
            d['gb300_reference_active_union_us']=b['active_union_median_us'] if b else ''
            d['b300_over_gb300']=r['active_union_median_us']/b['active_union_median_us'] if b else ''
            writer.writerow(d)
    plots(rows,baseline,output)
    source_links=[]
    for source in sources:
        dest=output/'source'/source.name
        dest.parent.mkdir(exist_ok=True)
        if source.is_dir():
            shutil.copytree(source,dest,dirs_exist_ok=True)
            source_links.append(f'<span>{esc(source.name)}/ included in the source tree</span>')
            continue
        shutil.copy2(source,dest)
        source_links.append(f'<a href="source/{esc(source.name)}">{esc(source.name)}</a>')
    copied_builder=output/'source'/'build_b300_report.py';copied_builder.parent.mkdir(exist_ok=True)
    (copied_builder.parent/'reference.json').write_text(json.dumps({'rows':baseline},indent=2)+'\n')
    if Path(__file__).resolve()!=copied_builder.resolve():shutil.copy2(__file__,copied_builder)
    source_links.append('<a href="source/build_b300_report.py">Report generator</a>')
    with zipfile.ZipFile(output/'reproduction-sources.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((output/'source').rglob('*')):
            if path.is_file():
                archive.write(path,path.relative_to(output))
    source_links.append('<a href="reproduction-sources.zip">All reproduction sources · ZIP</a>')
    original_set={r['m'] for r in baseline}; measured_set={r['m'] for r in rows}
    full = measured_set == original_set
    scope='Full 259-shape sweep' if full else f'{len(rows)} measured shapes · partial sweep'
    keys=('gpu','gpu_name','sm_count','compute_capability','architecture','cpu_architecture','torch','torch_version','cuda','cuda_version','driver','driver_version','nvcc','nsys','nsys_version','triton','deepgemm','deepgemm_version','deepgemm_package_version','deepgemm_commit','quant_source_sha256','quant_source_revision','quant_source_match','quant_source_identity','source_hashes','warmups','repeats','samples_per_shape','seed','clock_policy','power_limit_w','source_identity','metric','input_policy','nvtx_range_count','valid_sample_count','rejected_sample_count','status','started_at','completed_at','timestamp_utc')
    metadata_html=''.join(f'<dt>{esc(k.replace("_"," "))}</dt><dd><code>{esc(json.dumps(cleaned[k]) if isinstance(cleaned[k],(dict,list)) else cleaned[k])}</code></dd>' for k in keys if k in cleaned)
    limits=cleaned.get('limitations',[])
    if isinstance(limits,str):limits=[limits]
    limits = [
        'The rented B300 has 148 SMs on an x86 host; the retained GB300 reference has 152 SMs with an ARM host. GPU variant, clocks, power limit, CPU architecture and software build can affect the result.',
        'Quantization uses an isolated newer SGLang v2 JIT port, rather than the original production AOT v2 implementation. The operation and scale contract match, but this is not an exact production-image replay or an isolated hardware comparison.',
        'The DeepGEMM source commit is authoritative. It is b4296edce3cd07e3b6392c8eb390cee9c41a6b70 (commit message: Bump to v0.1.3); the installed package can report a different version string.',
        'The original curve aggregates two GB300 nodes at shared anchors; this reproduction uses one B300. A ratio below 1 means this measured B300 run was faster, not that every B300 is faster.',
        'Active-union median is the measured GPU time covered by the component kernels. Quantization and GEMM are means; their sum need not exactly equal the median composite.',
    ]+limits
    limitations_html=''.join(f'<p>{esc(x)}</p>' for x in limits)
    checks=cleaned.get('correctness',cleaned.get('validation'))
    check_html = esc(json.dumps(checks,ensure_ascii=False,indent=2)) if checks is not None else 'No correctness result was supplied to the report generator. See retained benchmark evidence.'
    anchors=[r for r in rows if r['m'] in {1,10,20,100,200,500,1000,2000,5000,10000}]
    if not anchors: anchors=rows[:min(10,len(rows))]
    table_head='<thead><tr><th>M · rows</th><th>B300 union · µs</th><th>Quant mean · µs</th><th>GEMM mean · µs</th><th>GB300 union · µs</th><th>B300 / GB300</th><th>Samples</th></tr></thead>'
    generated=datetime.now(timezone.utc).isoformat(timespec='seconds')
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>B300 dense-down kernel timing reproduction | MaaS Docs</title><meta name="description" content="Measured reproduction of the GLM-5.2 dense down-projection kernel-time curve on one rented B300, compared with the retained GB300 reference."><link rel="stylesheet" href="style.css"></head><body>
<header><div class="wrap"><p class="eyebrow">MaaS Docs · measured reproduction · 29 October 2026</p><h1>Dense down projection on one B300</h1><p>The same matrix-shape question on a newly rented GPU: how does kernel time grow as <i>M</i> changes, while <i>N</i> = 6144 and <i>K</i> = 1536 stay fixed?</p><a href="{BASE_URL}">Original GB300 tutorial and reference curve ↗</a></div></header>
<main class="wrap"><div class="cards"><div class="card"><span>Shape coverage</span><strong>{len(rows):,} / 259</strong><small>{'All reference M values measured' if full else 'Only measured points are plotted as B300'}</small></div><div class="card"><span>Measured composites</span><strong>{total_samples:,}</strong><small>GPU-resident timed samples</small></div><div class="card"><span>Matrix contract</span><strong>6144 × 1536</strong><small>Fixed N × K; BF16 → FP8 → BF16</small></div><div class="card"><span>Median timing ratio</span><strong>{ratio_text}</strong><small>B300 / GB300 over shared measured M</small></div></div>
<section class="panel"><div class="panel-head"><div><h2>Kernel time versus input rows</h2><p class="muted">B300 component means and active-union median, with the original GB300 composite curve. The horizontal axis is logarithmic; the vertical axis is linear.</p></div><span class="tag">{scope}</span></div><div class="notice"><strong>Comparability boundary.</strong> Matrix shapes, FP8 scale contract, DeepGEMM source revision and GPU-active timing metric match the reference. The quantization kernel is a newer isolated JIT port, so this is a controlled reimplementation rather than an exact replay of the original production image.</div><img class="chart" src="kernel-time.svg" alt="Measured B300 active-union, GEMM and quantization times across M, compared with the original GB300 active-union curve."><div class="downloads"><a href="kernel-time.svg">Vector chart · SVG</a><a href="kernel-time.png">Chart · PNG</a><a href="results.csv">Measured table · CSV</a><a href="results.json">Data and metadata · JSON</a></div><div class="anchors table-scroll"><table>{table_head}<tbody>{row_html(anchors,base)}</tbody></table></div><details><summary>All {len(rows)} measured shapes</summary><div class="table-scroll"><table>{table_head}<tbody>{row_html(rows,base)}</tbody></table></div></details></section>
<div class="two"><section class="panel"><h2>What was timed</h2><p>One logical dense-down invocation: online activation quantization followed by an FP8 DeepGEMM matrix multiplication. Each input shape is warmed before measured samples; host allocation, data transfers and correctness checks are outside the measurement ranges.</p><dl class="spec"><dt>Input</dt><dd>BF16 <code>[M, 1536]</code>, resident on the GPU</dd><dt>Weight</dt><dd>FP8 E4M3 <code>[6144, 1536]</code>, resident on the GPU</dd><dt>Scale format</dt><dd>Group/block 128; packed UE8M0 scale representation</dd><dt>Output</dt><dd>BF16 <code>[M, 6144]</code></dd><dt>Primary metric</dt><dd>Median GPU-active interval union of the quantization and GEMM kernels</dd><dt>Components</dt><dd>Mean quantization kernel and mean GEMM kernel time</dd><dt>Cache policy</dt><dd>No explicit L2 flush between samples</dd></dl><div class="notice"><strong>Not wall-clock latency.</strong> CUDA events around eager Python dispatch also include gaps between launches. They are not substituted for the Nsight kernel-time metric in this chart.</div></section>
<section class="panel"><h2>How to read the comparison</h2>{limitations_html}<h3>Correctness and validation evidence</h3><pre class="small" style="white-space:pre-wrap;overflow-wrap:anywhere">{check_html}</pre></section></div>
<section class="panel"><h2>Reproduction record</h2><p class="muted">Pinned software, measurement settings and source evidence supplied by this run.</p><dl class="meta">{metadata_html}</dl><div class="downloads">{''.join(source_links)}</div></section>
<footer>Generated {esc(generated)}. Reference: retained 19 August 2026 GB300 sweep. This page contains measured results only; omitted shapes are not interpolated as measurements.</footer></main></body></html>'''
    (output/'index.html').write_text(page)
    (output/'style.css').write_text(CSS)
    manifest={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (output/'manifest.json').write_text(json.dumps({'generated_at_utc':generated,'files':manifest},indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=BASELINE)
    p.add_argument('--source',type=Path,action='append',default=[],help='Copy a non-secret reproduction file or directory into source/')
    args=p.parse_args()
    rows,meta=normalized(json.loads(args.input.read_text()))
    baseline=baseline_rows(args.baseline)
    render(rows,baseline,meta,args.output,args.source)
    print(json.dumps({'output':str(args.output),'points':len(rows),'samples':sum(r['samples'] for r in rows),'reference_points':len(baseline)},indent=2))


if __name__=='__main__':
    main()
