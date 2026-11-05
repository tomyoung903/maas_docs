#!/usr/bin/env python3
"""Build the public report from verified, published experiment JSON."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/h20-tilesight-gemm-validation'
data=json.loads((OUT/'comparison.json').read_text())
baseline=json.loads((OUT/'baseline.json').read_text())
labels={'cube_2048':'Smaller cube','cube_8192':'Larger cube','tall':'Tall output','wide':'Wide output','long_k':'Longer reduction'}
rows=''
geometry=''
evidence=''
for r in data['cases']:
    shape=f'{r["m"]:,} × {r["n"]:,} × {r["k"]:,}'
    low=abs(r['error_pct'])
    rows+=f'<tr><td>{shape}<br><span class="small">{labels[r["name"]]}</span></td><td>{r["predicted_us"]/1000:.4f}</td><td>{r["device_cold_us"]/1000:.4f}</td><td class="error {"warn" if low>5 else ""}">{low:.2f}%</td></tr>\n'
    geometry+=f'<tr><td>{labels[r["name"]]}</td><td>{r["ctas"]:,}</td><td>{r["waves"]}</td><td>{r["k"]//64}</td></tr>\n'
    stem=f'evidence/{r["name"]}'
    evidence+=f'<tr><td>{labels[r["name"]]}</td><td><a href="{stem}/plan.json">Plan</a> · <a href="{stem}/prediction.json">Prediction</a></td><td><a href="{stem}/kernel-times.csv">Device samples</a> · <a href="{stem}/measurement.jsonl">Checks</a></td></tr>\n'
toc=[('results','Results'),('workload','Workload and tiles'),('model','Prediction walkthrough'),('measurement','Measurement'),('limits','What this establishes'),('reproduce','Reproduce and inspect')]
navigation=''.join(f'<a href="#{id}">{label}</a>' for id,label in toc)
template='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>H20 GEMM: TileSight prediction versus measurement | MaaS Docs</title>
<meta name="description" content="Five additional FP16 GEMMs on H20: 3.15% mean absolute prediction error, 9.15% worst error, fixed CUTLASS configuration and unchanged TileSight constants. Includes source, raw data, and the original 4096-cubed walkthrough.">
<link rel="stylesheet" href="style.css"></head><body>
<header><div class="wrap"><nav class="crumb"><a href="../">MaaS Docs</a> <span aria-hidden="true"> / </span> GPU performance models</nav>
<div class="hero"><div class="eyebrow">Hopper · FP16 GEMM · Experiment of 5 November 2026</div>
<h1>H20 GEMM: prediction meets measurement</h1>
<p class="lede">Five additional matrix shapes, one fixed CUTLASS kernel configuration, and unchanged TileSight timing constants. All five predictions were within 10% of measured kernel duration.</p>
<div class="stats"><div class="stat"><strong>@@MEAN@@%</strong><span>mean absolute prediction error</span></div><div class="stat"><strong>@@MAX@@%</strong><span>largest error · smallest cube</span></div><div class="stat"><strong>5 / 5</strong><span>correctness checks passed</span></div></div></div></div></header>
<div class="wrap layout"><aside class="toc" aria-label="Contents"><b>On this page</b>@@NAV@@</aside><main>
<section id="results"><h2>Five shapes, measured on H20</h2>
<p>Each measured value is the median of <strong>51 individual kernel durations</strong> from Nsight Systems, after cold-cache preparation. Predictions were saved before GPU execution. No parameter was fitted to these measurements.</p>
<div class="table-wrap"><table><thead><tr><th><span class="math-var">M × N × K</span></th><th>Predicted<br>ms</th><th>Measured<br>ms</th><th>Prediction<br>low by</th></tr></thead><tbody>@@ROWS@@</tbody></table></div>
<p class="small">Percent error uses measured time as the denominator. All five predictions are below the measured values. Averages are unweighted across these five selected cases.</p>
<div class="baseline"><strong>Earlier baseline: 4,096 × 4,096 × 4,096</strong><br>@@BASEP@@ ms predicted → @@BASEM@@ ms measured; @@BASEERR@@% low. This earlier case is excluded from the five-case average.</div>
<p>The tall and wide cases have the same FLOP count and almost the same measured time. The largest cube and longer-reduction case agree within 0.2%. The smallest cube has the largest relative error.</p>
<div class="downloads"><a class="button" href="comparison.csv" download>Download comparison CSV</a><a class="button" href="comparison.json">Inspect full results</a></div></section>

<section id="workload"><h2>The workload and tile configuration</h2>
<p class="math"><span class="math-mat">C</span> = <span class="math-mat">A</span><span class="math-mat">B</span>, with <span class="math-mat">A</span> ∈ ℝ<sup><span class="math-var">M × K</span></sup>, <span class="math-mat">B</span> ∈ ℝ<sup><span class="math-var">K × N</span></sup>, and <span class="math-mat">C</span> ∈ ℝ<sup><span class="math-var">M × N</span></sup>.</p>
<p>Inputs and output are row-major FP16. Accumulation is FP32. Each CTA owns a <strong>128 × 128 output tile</strong> and advances through K in steps of 64, with three pipeline stages.</p>
<div class="flow" aria-label="Tile execution data flow"><div><strong>Load A tile</strong><span>Global memory → shared memory, through TMA</span></div><div><strong>Load B tile</strong><span>Global memory → shared memory, through TMA</span></div><div class="wide"><strong>Matrix multiply and accumulate</strong><span>Hopper WGMMA · FP32 accumulator in registers · repeat over K</span></div><div><strong>Convert output</strong><span>FP32 → FP16 in registers</span></div><div><strong>Store C tile</strong><span>Registers → global memory</span></div></div>
<ul><li>One NVIDIA H20 with 78 SMs; 256 threads per CTA; cluster shape 1 × 1 × 1.</li><li>One output tile per CTA, with M varying fastest in the logical grid. No split-K or cooperative CTA pair.</li><li>One compiled kernel configuration handles all five shapes through runtime dimensions.</li><li>CUDA reports a maximum of one resident CTA per SM for this kernel. It uses 164 registers per thread and 98,432 bytes of dynamic shared memory. The compiler reports no spills; the trace reports no local-memory allocation.</li></ul>
<div class="table-wrap"><table><thead><tr><th>Case</th><th>CTAs</th><th>Modeled waves</th><th>K steps / tile</th></tr></thead><tbody>@@GEOMETRY@@</tbody></table></div>
<p class="small">Modeled waves = ceiling(CTAs / 78). TileSight uses the default full-wave tail policy. This is a scheduling approximation, not a claim that hardware enforces synchronized waves.</p></section>

<section id="model"><h2>Walk through the original 4,096³ prediction</h2>
<p>The H20 microbenchmark profile provides 139.22 TFLOP/s of FP16 Tensor Core throughput. At one CTA per SM, the modeled service time for one tile’s K step is:</p>
<div class="equation math"><div>Work per step = 2 × 128 × 128 × 64 = 2,097,152 FLOPs</div><div>Time per step = 2,097,152 / (139.22 × 10<sup>12</sup> / 78)</div><div class="answer">= 1.17495946 µs</div></div>
<p>For this compute-dominated plan, most input loading overlaps with computation. The complete modeled tile time includes the initial loads and output handling:</p>
<div class="equation"><div class="math">64 × 1.17495946 µs <span class="small">· K-step computation</span></div><div class="math">+ 0.15731644 + 0.15731644 µs <span class="small">· initial A and B loads</span></div><div class="math">+ 0.08743549 + 0.59370592 µs <span class="small">· output conversion and store</span></div><div class="answer math">= 76.19317972 µs per tile</div></div>
<p>There are 32 × 32 = 1,024 CTAs and ceiling(1,024 / 78) = 14 modeled waves:</p>
<div class="equation math"><div>Predicted body = 14 × 76.19317972 µs</div><div class="answer">= 1,066.704516 µs ≈ 1.067 ms</div></div>
<p>The baseline measured 1.102 ms. Its resource-bound and best-periodic-schedule modes gave the same prediction for this plan. The default 2 µs launch term is excluded when comparing against device kernel duration.</p></section>

<section id="measurement"><h2>How the measurements were checked</h2>
<div class="two"><div><h3>Numerical correctness</h3><p>cuBLAS computes the same matrix product independently. Its output is compared with the CUTLASS output before timing. Every output element matched exactly for the deterministic test inputs.</p><p class="small">The inputs are multiples of 1/8. Exact agreement on this fixture does not imply bitwise agreement for arbitrary floating-point data. cuBLAS runtime is not the performance baseline.</p></div><div><h3>Timing</h3><p>Each case has a normal run and a separate Nsight Systems run: 100 warmup launches, 51 repeated-input samples, and 51 samples with cold-cache preparation.</p><p class="small">Allocation, transfers, correctness checks, warmups, and the cache-flush kernel are outside the reported intervals.</p></div></div>
<p>Cold preparation reads and writes a separate 512 MiB buffer. It is an eviction procedure, not a guarantee that every subsequent input load misses cache. Normal runs also measure 11 replays of a 20-kernel CUDA Graph; those values and CUDA-event timings are in the downloadable results.</p>
<p>The trace extractor verifies shape, grid dimensions, thread count, occupancy, and launch count. It excludes the correctness launch and all warmups. The table above uses actual device kernel start-to-end durations.</p></section>

<section id="limits"><h2>What this establishes</h2><div class="note"><strong>A useful starting point for this H20 kernel family.</strong> Five selected shapes agree within 10%, using the same implementation and model constants. The original baseline gives a sixth, separate example.</div>
<ul><li>This does not validate arbitrary shapes, other tile configurations, different precisions, other GPUs, or tiny single-CTA workloads.</li><li>The close results do not establish that every modeled component is correct. Individual modeling errors can cancel.</li><li>TileSight still approximates cache behavior, instruction scheduling, synchronization, and some internal data movement.</li><li>The model declares 98,304 bytes of input buffers; the real kernel also has pipeline metadata. The difference does not change occupancy here.</li><li>The profile’s microbenchmark clock field is 1,743 MHz; observed GPU clocks under load were 1,980 MHz. Existing throughput and bandwidth constants were retained, so this is not a fresh calibration of this device.</li></ul>
<p>No clock, power-limit, service, or system-package changes were made. The benchmark processes have exited.</p></section>

<section id="reproduce"><h2>Reproduce and inspect</h2>
<div class="downloads"><a class="button" href="reproduction.zip" download>Download source bundle</a><a class="button" href="source/README.md">Reproduction guide</a><a class="button" href="cases.json">Fixed case list</a></div>
<p>The bundle contains the benchmark, prediction runner, bounded GPU runner, trace extractor, and case list. It does not contain CUDA, CUTLASS, or TileSight dependencies. The guide pins their source versions.</p>
<div class="table-wrap"><table><thead><tr><th>Case</th><th>Model</th><th>Measurement</th></tr></thead><tbody>@@EVIDENCE@@</tbody></table></div>
<h3>Source versions</h3><ul class="provenance"><li><a href="https://github.com/tile-ai/TileSight/pull/1">H20 profile correction</a>: WGMMA capability and nominal memory capacity. Timing constants were unchanged. <a href="https://github.com/tomyoung903/TileSight/commit/71c51b223230b4bc13cfcaf3cb1ca25363e6ffb9">Experiment revision</a>.</li><li><a href="https://github.com/NVIDIA/cutlass/tree/954c8d7be60d730cc3f51e8f1ffe9850dce054d5">Pinned CUTLASS revision</a>; CUDA 12.8; native <code>sm_90a</code>; optimization enabled and assertions disabled.</li><li>Model options: <code>cache="fast"</code>, <code>ii_mode="periodic_best"</code>, explicit residency of one, default full-wave tail policy.</li></ul>
</section><footer>Generated from archived experiment data. Five-case results: 5 November 2026. <a href="SHA256SUMS">Artifact checksums</a>.</footer>
</main></div>
  <script defer src="../assets/maas-annotator.js" data-maas-annotator data-page-key="/h20-tilesight-gemm-validation/"></script>
</body></html>'''
replacements={'MEAN':f'{data["mean_absolute_percent_error"]:.2f}','MAX':f'{data["max_absolute_percent_error"]:.2f}',
              'NAV':navigation,'ROWS':rows,'GEOMETRY':geometry,'EVIDENCE':evidence,
              'BASEP':f'{baseline["predicted_us"]/1000:.4f}','BASEM':f'{baseline["device_cold_us"]/1000:.4f}',
              'BASEERR':f'{abs(baseline["error_pct"]):.2f}'}
for key,value in replacements.items(): template=template.replace('@@'+key+'@@',value)
assert '@@' not in template
(OUT/'index.html').write_text(template)
with zipfile.ZipFile(OUT/'reproduction.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted((OUT/'source').iterdir()):
        if p.is_file():
            info=zipfile.ZipInfo(p.name, date_time=(2026,11,5,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes())
    info=zipfile.ZipInfo('cases.json', date_time=(2026,11,5,0,0,0))
    info.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(info,(OUT/'cases.json').read_bytes())
(OUT/'SHA256SUMS').write_text(''.join(
    f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n'
    for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'
))
print(OUT/'index.html')
