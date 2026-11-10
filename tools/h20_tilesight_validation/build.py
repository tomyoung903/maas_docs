#!/usr/bin/env python3
"""Render a single-case explanation from the original archived analysis."""
import html
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.h20_gemm_utilization import utilization_section
OUT = ROOT / 'docs/h20-tilesight-gemm-validation'
d = json.loads((OUT/'data/numbers.json').read_text())
ops = {x['id']: x for x in d['ops']}
repo = 'https://github.com/tomyoung903/TileSight/blob/71c51b223230b4bc13cfcaf3cb1ca25363e6ffb9/'
toc = [('setup','1 · The input'),('tiles','2 · Divide the work'),('plan','3 · Describe one tile'),('costs','4 · Price the operations'),('overlap','5 · Overlap the K steps'),('grid','6 · Schedule the grid'),('l2-reuse','6b · Explore L2 reuse'),('result','7 · Compare with measurement'),('source','Code and saved data')]
toc.append(('utilization', '8 · Utilization rates'))
nav = ''.join(f'<a href="#{key}">{text}</a>' for key,text in toc)
resources = ['ddr','l2','smem','tma','tensor','cuda','register','ldst']
resource_rows = ''
for name in ['load_A','load_B','mma','cast_C','store_C']:
    o=ops[name]
    values=''.join(f'<td>{o["resources_us"][r]:.6f}</td>' if r in o['resources_us'] else '<td>—</td>' for r in resources)
    resource_rows += f'<tr><th><code>{name}</code></th>{values}<td><strong>{o["completion_us"]:.6f}</strong></td></tr>'

def timeline(last=False):
    ii=d['ii_us']; offsets=d['offsets_us']
    start=62*ii if last else 0
    stop=d['tile_us'] if last else 4*ii+offsets['mma']
    width=880; left=130; scale=(width-left-25)/(stop-start)
    bars=[]
    for k in (range(62,64) if last else range(4)):
        for op,y,label,color in [('load_A',36,'A','#2d7f9a'),('load_B',36,'B','#639ab0'),('mma',95,'MMA','#16756c')]:
            t=k*ii+offsets[op]; end=t+ops[op]['completion_us']
            x=left+(t-start)*scale; w=(end-t)*scale
            bars.append(f'<rect x="{x:.3f}" y="{y}" width="{w:.3f}" height="36" rx="3" fill="{color}"><title>{op}, K step {k}: {t:.6f}–{end:.6f} µs</title></rect>')
            if op=='mma':bars.append(f'<text x="{x+w/2:.3f}" y="{y+23}" text-anchor="middle" fill="white" font-size="13">{label} {k}</text>')
    if last:
        t=64*ii+offsets['mma']
        for name,label in [('cast_C','cast'),('store_C','store')]:
            x=left+(t-start)*scale; w=ops[name]['completion_us']*scale
            bars.append(f'<rect x="{x:.3f}" y="154" width="{w:.3f}" height="36" rx="3" fill="#98661d"><title>{label}: {t:.6f}–{t+ops[name]["completion_us"]:.6f} µs</title></rect>')
            if w>40:bars.append(f'<text x="{x+w/2:.3f}" y="177" text-anchor="middle" fill="white" font-size="13">{label}</text>')
            t+=ops[name]['completion_us']
    ticks=[]
    for i in range(6):
        x=left+(width-left-25)*i/5;t=start+(stop-start)*i/5
        ticks.append(f'<line x1="{x}" x2="{x}" y1="22" y2="199" stroke="#dbe5e8"/><text x="{x}" y="221" text-anchor="middle" fill="#516575" font-size="12">{t:.2f}</text>')
    return f'<svg viewBox="0 0 880 245" role="img" aria-label="Modeled schedule, {"last" if last else "first"} K steps; time in microseconds"><text x="6" y="59">Load actor</text><text x="6" y="118">Tensor actor</text><text x="6" y="177">Output actor</text>{"".join(ticks)}{"".join(bars)}<text x="845" y="240" fill="#516575" font-size="12">µs</text></svg>'

example='''arch = H20().set_to_microbench()
program = gemm_program(
    m=4096, n=4096, k=4096,
    block_m=128, block_n=128, block_k=64,
    stages=3, dtype="fp16", accumulation_dtype="fp32",
)
program = replace(program, launches=(replace(
    program.launches[0], requires_arch=("wgmma",), residency=1,
),))
result = sight.analyze(
    program, arch,
    options=sight.Options(cache="fast", ii_mode="periodic_best"),
)'''
recipe='''with kb.loop("k", 64, stages=3) as loop:
    kb.copy(A["m", "k"], A_s, name="load_A")
    kb.copy(B["k", "n"], B_s, name="load_B")
    kb.gemm(A_s, B_s, acc, name="mma", ...)
    with loop.epilogue():
        kb.cast(acc, C_r, name="cast_C", actor="epilogue")
        kb.copy(C_r, C["m", "n"], name="store_C", engine="ldst")'''
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>How TileSight predicts a 4096³ GEMM on H20 | MaaS Docs</title>
<meta name="description" content="A worked single-case explanation: matrix shape to CTA tiles, operation resource times, pipeline overlap, 14 waves, and a 1.066705 ms prediction on H20.">
<link rel="stylesheet" href="style.css"><link rel="stylesheet" href="walkthrough.css?v=l2-reuse-20261110"></head><body>
<header><div class="wrap"><nav class="crumb"><a href="../">MaaS Docs</a> / GPU performance modeling</nav><div class="hero"><div class="eyebrow">A worked example · H20 · 4,096 × 4,096 × 4,096</div><h1>How TileSight arrives at 1.067 ms</h1><p class="lede">Follow one GEMM from its matrix dimensions to the final prediction. Every number below comes from the original 4K-cubed run, or is arithmetic using that run’s configuration.</p><div class="path">Matrix shape <span>→</span> one tile’s plan <span>→</span> operation costs <span>→</span> overlapping K steps <span>→</span> the whole grid</div></div></div></header>
<div class="wrap layout"><aside class="toc" aria-label="Contents"><b>This calculation</b>@@NAV@@</aside><main>
<section id="setup"><h2>1. Start with an explicit configuration</h2><div class="equation math"><div><b>C</b> = <b>A</b><b>B</b>, &nbsp; <i>M</i> = <i>N</i> = <i>K</i> = 4,096</div><div>FP16 inputs and output · FP32 accumulation</div></div><p>There are no quantization scales, bias, or activation functions. This H20 path accumulates in ordinary registers, not Blackwell Tensor Memory.</p><p>We supplied a <strong>128 × 128 output tile</strong>, a <strong>64-element K step</strong>, and <strong>three pipeline stages</strong>. TileSight did not search for those dimensions. The actual CUTLASS kernel uses the same choices.</p><details><summary>Show the Python call used to describe this GEMM</summary><pre><code>@@EXAMPLE@@</code></pre></details><p class="small">“Residency = 1” means one concurrent CTA per SM. We set it explicitly after checking that the compiled kernel permits one.</p></section>

<section id="tiles"><h2>2. Divide the output, then divide K</h2><div class="two"><div><h3>Across the GPU</h3><div class="equation math">(4,096 / 128) × (4,096 / 128)<br>= 32 × 32 = 1,024 output tiles</div><p>Each tile belongs to one CTA, also called a thread block. A CTA runs on one SM; it is not permanently assigned to a particular SM number.</p></div><div><h3>Inside one CTA</h3><div class="equation math">4,096 / 64 = 64 K steps</div><p>The CTA keeps its 128 × 128 output accumulator while walking through K. Each step adds another product to that same accumulator.</p></div></div>
<div class="tile-demo"><h3>Inspect a tile and one K step</h3><div class="controls"><label>Tile row <input id="tile-m" type="range" min="0" max="31" value="0"><output id="m-value">0</output></label><label>Tile column <input id="tile-n" type="range" min="0" max="31" value="0"><output id="n-value">0</output></label><label>K step <input id="tile-k" type="range" min="0" max="63" value="0"><output id="k-value">0</output></label></div>
<div class="tile-readout"><svg viewBox="0 0 288 288" role="img" aria-label="The output matrix divided into a 32 by 32 grid"><defs><pattern id="output-tile-grid-pattern" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M 8 0 L 0 0 0 8" fill="none" stroke="#b8d0d5" stroke-width=".6"/></pattern></defs><rect x="16" y="16" width="256" height="256" fill="#edf6f5"/><rect x="16" y="16" width="256" height="256" fill="url(#output-tile-grid-pattern)"/><rect id="selected-tile" x="16" y="16" width="8" height="8" fill="#146b67"/></svg><div><p id="c-range" class="math"></p><p id="a-range" class="math"></p><p id="b-range" class="math"></p><p class="small">Ranges use Python’s end-exclusive convention. Sliders inspect the fixed plan; they do not rerun the performance model.</p></div></div></div>
<p>For tile (0, 0), the first step multiplies A[0:128, 0:64] by B[0:64, 0:128]. The next step uses K positions 64:128. After all 64 steps, the output tile contains the full dot products.</p></section>

<section id="plan"><h2>3. Write the tile execution plan</h2><p>The GEMM example builder declares five operation types. It records them for analysis; it does not inspect the compiled CUDA kernel to discover them.</p><div class="flow"><div><strong>Load A</strong><span>128 × 64 FP16 values → shared memory</span></div><div><strong>Load B</strong><span>64 × 128 FP16 values → shared memory</span></div><div class="wide"><strong>MMA: multiply and accumulate</strong><span>Update 128 × 128 FP32 values in registers</span></div><div><strong>Cast C</strong><span>Convert the final accumulator to FP16</span></div><div><strong>Store C</strong><span>Write 128 × 128 FP16 values to global memory</span></div></div>
<p><strong>Load A, load B, and MMA repeat 64 times.</strong> Cast and store run once, after the loop. An epilogue in the builder describes that final work.</p><details><summary>Show the builder’s operation sequence</summary><pre><code>@@RECIPE@@</code></pre><p class="small">This excerpt fixes the loop count to this example and omits optional GEMM arguments. It is a plan-building sketch, not executable GPU code.</p></details>
<div class="table-wrap"><table><thead><tr><th>Quantity</th><th>Arithmetic</th><th>Per CTA</th></tr></thead><tbody><tr><td>One A or B load</td><td>128 × 64 × 2 bytes</td><td>16 KiB</td></tr><tr><td>Three stages of A and B</td><td>3 × (16 + 16) KiB</td><td>96 KiB shared</td></tr><tr><td>FP32 accumulator</td><td>128 × 128 × 4 bytes</td><td>64 KiB logical data</td></tr><tr><td>Final FP16 output</td><td>128 × 128 × 2 bytes</td><td>32 KiB</td></tr><tr><td>One MMA step</td><td>2 × 128 × 128 × 64</td><td>2,097,152 FLOPs</td></tr></tbody></table></div><p class="small">The accumulator is distributed across threads. Its logical size is not the kernel’s total register allocation. The factor 2 counts a multiply and an add.</p></section>

<section id="costs"><h2>4. Convert work and traffic into resource times</h2><p>For each operation, TileSight estimates time demanded from each hardware resource. These entries form its <strong>resource-time vector</strong>. They are modeled service times, not separately measured durations.</p><div class="equation math"><div>Resource time = work / throughput</div><div>Memory resource time = bytes handled at that level / its bandwidth share</div></div>
<p>The run used the repository’s <code>H20().set_to_microbench()</code> constants unchanged:</p><div class="table-wrap"><table><thead><tr><th>Resource</th><th>Whole-device model rate</th><th>Share for one CTA here</th></tr></thead><tbody><tr><td>FP16 Tensor Core work</td><td>139.22 TFLOP/s</td><td>139.22 / 78 TFLOP/s</td></tr><tr><td>HBM (called DDR in code)</td><td>4.305 TB/s</td><td>55.1923 GB/s</td></tr><tr><td>L2 requests</td><td>8.123448629 TB/s</td><td>104.1468 GB/s</td></tr><tr><td>Shared-memory ports</td><td>19.768320312 TB/s summed</td><td>253.4400 GB/s</td></tr><tr><td>FP32 CUDA arithmetic</td><td>29.231883 TFLOP/s</td><td>Used to price conversion below</td></tr></tbody></table></div>
<p>Why divide by 78? The model has 78 active SMs and one resident CTA per SM. It shares device-wide HBM and L2 rates equally, and converts the summed compute and shared-memory rates into per-SM rates. It does not mean HBM is physically divided into 78 private memories.</p>
<h3>Work through one 16 KiB A load</h3><p>The cache model assigns an average of 324.54 HBM bytes to each A load, while all 16,384 bytes generate L2 read requests and shared-memory writes. Cached reuse explains the different byte counts.</p><div class="equation math"><div><i>t</i><sub>HBM</sub> = 324.5426 / (4.305 × 10<sup>12</sup> / 78) = 0.005880 µs</div><div><i>t</i><sub>L2</sub> = 16,384 / (8.123448629 × 10<sup>12</sup> / 78) = 0.157316 µs</div><div><i>t</i><sub>SMEM</sub> = 16,384 / (19.768320312 × 10<sup>12</sup> / 78) = 0.064646 µs</div><div class="answer"><i>t</i><sub>load A</sub> = max(0.005880, 0.157316, 0.064646, 0.064646) = 0.157316 µs</div></div>
<p>The fourth entry is TMA service. This run has no independent TMA rate, so the implementation uses the shared-memory port rate as a proxy.</p><p><strong>These are not three serial journey segments to add.</strong> They are demands on HBM, L2, and shared-memory resources. The move-cost model takes their maximum, plus any explicit extra latency. Extra latency is zero in this run. The full loop model then considers resource contention and dependencies between operations.</p>
<details><summary>Why do A and B have different HBM byte counts?</summary><p>The grid traversal determines reuse. Adjacent output tiles can reuse input tiles through L2. The sampled cache model estimates 324.54 HBM bytes per A load and 1,391.12 per B load, averaged across the grid. These are model estimates, not literal fractional memory transactions or a measured cache trace.</p><p>The cache trace is approximate and starts cold. Both loads are L2-limited under these estimated rates, so they receive the same 0.157316 µs completion time.</p></details>
<h3>The five operation costs</h3><p class="small">All entries below are µs per execution. “—” means no explicit resource charge in this plan; compute-internal memory traffic is not fully described.</p><div class="table-wrap wide-table"><table><thead><tr><th>Operation</th><th>HBM</th><th>L2</th><th>SMEM</th><th>TMA</th><th>Tensor</th><th>CUDA</th><th>Registers</th><th>LD/ST</th><th>Completion</th></tr></thead><tbody>@@RESOURCES@@</tbody></table></div>
<details><summary>Show the MMA, cast, and store arithmetic</summary><div class="equation math"><div><i>t</i><sub>MMA</sub> = 2,097,152 / (139.22 × 10<sup>12</sup> / 78) = 1.174959 µs</div><div><i>t</i><sub>cast</sub> = 16,384 / (29.231883 × 10<sup>12</sup> / 2 / 78) = 0.087435 µs</div><div><i>t</i><sub>store</sub> = 32,768 / (4.305 × 10<sup>12</sup> / 78) = 0.593706 µs</div></div><p>Cast is priced as one CUDA instruction unit per value. The code divides the FP32 FMA FLOP/s convention by two to obtain an instruction rate. This is a model approximation, not a dedicated measured cast throughput.</p><p>For the store, HBM service is the largest resource time. The plan charges all 32 KiB to HBM and L2 writes; register-read and LD/ST proxy times are smaller.</p></details></section>

<section id="overlap"><h2>5. Overlap loading with the K loop</h2><p>Adding all five costs and multiplying by 64 would be wrong. Output work happens once, and input loads can overlap with the preceding MMA. The three stages supply reusable input buffers.</p><p>The solver finds a periodic schedule with an <strong>initiation interval, II, of 1.174959 µs</strong>. II is the time between starting consecutive K iterations. Here, tensor work sets that interval.</p><div class="equation math"><div>Per iteration: L2 demand = 0.157316 + 0.157316 = 0.314633 µs</div><div>Per iteration: tensor demand = 1.174959 µs</div><div class="answer">Selected II = 1.174959 µs</div></div><p>The solver also checks that data is ready, the accumulator recurrence is respected, and buffers can be reused. It does not choose II from resource totals alone.</p>
<div class="schedule"><div class="schedule-controls"><button type="button" data-view="first" aria-pressed="true">First four K steps</button><button type="button" data-view="last" aria-pressed="false">Last two + output</button></div><div id="schedule-first">@@FIRST@@</div><div id="schedule-last" hidden>@@LAST@@</div><p class="small">This is TileSight’s constructed schedule, not a GPU profiler trace. Blue bars are A then B loads; green bars are MMA. Hover a bar for its modeled start and end time. A model actor is a scheduling role, not an individual SM.</p></div>
<p>In the first iteration, A starts at 0, B at 0.157316, and MMA at 0.314633 µs. The next iteration starts at 1.174959 µs, so its loads overlap with the previous MMA.</p><div class="equation math"><div><i>T</i><sub>tile</sub> = initial loads + 64 × II + final cast + final store</div><div>= 0.15731644 + 0.15731644 + 64 × 1.17495946</div><div>&nbsp; + 0.08743549 + 0.59370592</div><div class="answer">= 76.19317972 µs</div></div><p>The last MMA finishes at 75.512038 µs. Cast finishes at 75.599474 µs, then the store completes the tile at 76.193180 µs.</p></section>

<section id="grid"><h2>6. Schedule 1,024 tiles on 78 SMs</h2><p>The kernel permits one resident CTA per SM. The model therefore has 78 concurrent slots. It assigns the next tile to the earliest free slot.</p><div class="equation math"><div>1,024 = 13 × 78 + 10</div><div>Modeled waves = ⌈1,024 / 78⌉ = 14</div><div class="answer"><i>T</i><sub>kernel body</sub> = 14 × 76.19317972 = 1,066.704516 µs</div></div><div class="wave-row" aria-label="Thirteen full waves followed by one wave with ten tiles">@@WAVES@@</div><p>After 13 full waves, ten tiles remain. They still take one tile duration. They do not take 10/78 of that duration, because each must finish all 64 K steps.</p><p class="small">This run uses <code>full_wave_costs</code>: even the last ten CTAs retain the full-wave resource shares. “Wave” is the model’s useful grouping here, not a hardware-wide synchronization barrier.</p></section>

<section id="result"><h2>7. Compare like-for-like timing</h2><div class="stats"><div class="stat"><strong>1.066705 ms</strong><span>TileSight kernel-body prediction</span></div><div class="stat"><strong>1.101956 ms</strong><span>Measured device kernel duration</span></div><div class="stat"><strong>3.20% low</strong><span>Prediction error / measured time</span></div></div><p>The measured value is the median of 51 Nsight Systems samples with cold-cache preparation. Allocations, correctness checks, warmup, and cache-flush execution are outside those kernel intervals.</p><p>TileSight also reports 1.068705 ms when its default 2 µs launch term is included. We use <strong>1.066705 ms</strong> for the comparison to device-only kernel duration.</p><div class="note">The result supports this specific tile-level model as a useful starting point. It does not prove each substep’s modeled duration: individual instructions, barriers, parts of internal memory traffic, and real cache behavior remain approximate.</div><p>The model rates were not fitted to this result. The profile’s clock field is 1,743 MHz, while the GPU ran near 1,980 MHz under load; we kept the existing throughput constants. This is not a fresh hardware calibration.</p></section>

<section id="source"><h2>Connect each step to the code</h2><p>This page uses the saved original analysis. It introduces no new GPU measurements.</p><div class="table-wrap"><table><thead><tr><th>Question</th><th>Implementation</th></tr></thead><tbody><tr><td>Who declares the five operations?</td><td><a href="@@REPO@@tilesight/modeling/program/examples/gemm.py">GEMM example builder</a></td></tr><tr><td>Where are the hardware rates?</td><td><a href="@@REPO@@tilesight/arch/h20.py">H20 profile</a></td></tr><tr><td>How are operations priced?</td><td><a href="@@REPO@@tilesight/modeling/program/generic_oracle.py">Generic operation cost model</a></td></tr><tr><td>How are tiles assigned to slots?</td><td><a href="@@REPO@@tilesight/modeling/program/spatial.py">Spatial scheduling</a></td></tr><tr><td>Where is the recorded overlap schedule?</td><td><a href="data/periodic_best.json">Full analysis snapshot</a></td></tr></tbody></table></div><div class="downloads"><a class="button" href="data/numbers.json">Numbers used on this page</a><a class="button" href="data/plan.json">Recorded tile plan</a><a class="button" href="data/prediction-summary.json">Prediction summary</a><a class="button" href="data/measurement.jsonl">Original correctness and timing log</a></div><p class="small">This walkthrough explains only the original 4K-cubed case. The later five-case measurements remain available as <a href="comparison.csv">archived comparison data</a>.</p></section>
<footer>Original experiment: 5 November 2026 · H20 · FP16 GEMM · Times shown with rounded decimal values.</footer></main></div>
<script src="walkthrough.js?v=l2-reuse-20261110" defer></script>
  <script defer src="../assets/maas-annotator.js" data-maas-annotator data-page-key="/h20-tilesight-gemm-validation/"></script>
</body></html>'''
page = page.replace('Every number below comes from the original 4K-cubed run, or is arithmetic using that run’s configuration.', 'The timing calculation preserves the original 4K-cubed run; the L2 explorer adds a later full-access cache calculation.')
reuse_section = (Path(__file__).parent/'l2-reuse-section.html').read_text()
assert page.count('<section id="result">') == 1
page = page.replace('<section id="result">', reuse_section + '\n<section id="result">')
page = page.replace('<footer>', utilization_section(OUT, d['shape'], d['measured_us'], 'cold-cache preparation') + '\n<footer>', 1)
substitutions={'NAV':nav,'EXAMPLE':html.escape(example),'RECIPE':html.escape(recipe),'RESOURCES':resource_rows,'FIRST':timeline(),'LAST':timeline(True),'REPO':repo,'L2REV':hashlib.sha256((OUT/'assets/l2-reuse.html').read_bytes()).hexdigest()[:12],'WAVES':''.join(f'<span class="wave {"tail" if i==14 else ""}" title="Wave {i}: {10 if i==14 else 78} CTAs">{i}<small>{10 if i==14 else 78}</small></span>' for i in range(1,15))}
for k,v in substitutions.items():page=page.replace('@@'+k+'@@',v)
assert '@@' not in page
assert abs(d['tile_us']*14-d['kernel_us'])<1e-8
assert abs(sum(ops[n]['completion_us'] for n in ['load_A','load_B','cast_C','store_C'])+64*d['ii_us']-d['tile_us'])<1e-8
(OUT/'index.html').write_text(page)
(OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n' for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS'))
print(OUT/'index.html')
