"""Render comparable, workload-derived utilization summaries for the H20 pages."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'docs/h20-tilesight-memory-bound/data'
PEAK_FP16_FLOPS = 148e12


def utilization_section(out, shape, measured_us, preparation):
    """Use saved device time, not the prediction or a profiler utilization counter."""
    m, n, k = shape
    assert min(m, n, k, measured_us) > 0
    calibration = json.loads((REFERENCE / 'bandwidth-calibration.json').read_text())
    board = json.loads((REFERENCE / 'board-bandwidth.json').read_text())
    measured_bandwidth = calibration['selected_bandwidth_Bps']
    nominal_bandwidth = board['memoryBandwidth']
    seconds = measured_us * 1e-6
    flops = 2 * m * n * k
    # C = A @ B with FP16 A, B and C: read A/B once and write C once.
    useful_bytes = 2 * (m * k + k * n + m * n)
    achieved_flops = flops / seconds
    achieved_bandwidth = useful_bytes / seconds
    compute_pct = 100 * achieved_flops / PEAK_FP16_FLOPS
    nominal_pct = 100 * achieved_bandwidth / nominal_bandwidth
    measured_pct = 100 * achieved_bandwidth / measured_bandwidth
    data = {
        'shape_mnk': list(shape), 'measured_kernel_us': measured_us,
        'measurement_preparation': preparation, 'flops': flops,
        'useful_bytes': useful_bytes, 'achieved_flops_per_s': achieved_flops,
        'useful_bandwidth_Bps': achieved_bandwidth,
        'reported_dense_fp16_peak_flops_per_s': PEAK_FP16_FLOPS,
        'nominal_board_bandwidth_Bps': nominal_bandwidth,
        'measured_bandwidth_reference_Bps': measured_bandwidth,
        'flop_utilization_pct': compute_pct,
        'useful_bandwidth_nominal_utilization_pct': nominal_pct,
        'useful_bandwidth_measured_reference_utilization_pct': measured_pct,
        'traffic_definition': '2*(M*K+K*N+M*N): FP16 A/B read once and C written once',
        'limitation': 'Useful-byte ratio, not counter-measured total HBM utilization; excludes refetches and other traffic',
        'reference_sources': {
            'nominal_bandwidth': '../h20-tilesight-memory-bound/data/board-bandwidth.json',
            'measured_bandwidth': '../h20-tilesight-memory-bound/data/bandwidth-calibration.json',
            'compute_peak': 'Reported 148 TFLOP/s dense FP16 peak used in these H20 experiment pages',
        },
    }
    (out / 'data/utilization.json').write_text(json.dumps(data, indent=2) + '\n')
    return f'''<section id="utilization"><h2>8. FLOP and bandwidth utilization</h2>
<p>Both rates below use the <strong>measured device-only median of {measured_us:,.3f} µs</strong> ({html.escape(preparation)}), not TileSight’s predicted time. They use the whole GPU’s reference rates.</p>
<div class="two"><div class="baseline"><b>FLOP utilization</b><div class="equation math"><strong>{compute_pct:.2f}%</strong><br>{achieved_flops / 1e12:.4f} TFLOP/s ÷ 148 TFLOP/s</div><p class="small">Useful GEMM work divided by the reported dense FP16 Tensor Core peak.</p></div>
<div class="baseline"><b>Bandwidth utilization · useful bytes</b><div class="equation math"><strong>{nominal_pct:.2f}%</strong><br>{achieved_bandwidth / 1e12:.6f} TB/s ÷ {nominal_bandwidth / 1e12:.6f} TB/s</div><p class="small">Relative to the nominal board HBM rate. Against our independently measured {measured_bandwidth / 1e12:.9f} TB/s reference, the same throughput is <strong>{measured_pct:.2f}%</strong>.</p></div></div>
<div class="equation math"><div>GEMM work = 2MNK = {flops:,} FLOPs</div><div>Useful bytes = 2(MK + KN + MN) = {useful_bytes:,} bytes</div><div>Measured time = {measured_us:,.3f} × 10<sup>−6</sup> seconds</div><div>FLOP utilization (%) = work ÷ measured time ÷ (148 × 10<sup>12</sup>) × 100</div><div>Useful-byte bandwidth utilization (%) = useful bytes ÷ measured time ÷ ({nominal_bandwidth / 1e12:.6f} × 10<sup>12</sup>) × 100</div></div>
<p>The byte count reads each FP16 A and B element once and writes each FP16 C element once. It excludes repeated HBM fetches, cache writebacks, and other traffic. Therefore this is a <strong>useful-byte bandwidth ratio, not a hardware-counter measurement of total HBM utilization</strong>. A low ratio can coexist with additional HBM traffic or substantial L2 reuse.</p>
<p class="small">The 148 TFLOP/s peak differs from TileSight’s 139.22 TFLOP/s calibration. The nominal and measured bandwidth references also differ. These consistent end-of-page comparisons do not change any earlier model inputs or timings. This A+B+C byte count differs from a B-only throughput calculation.</p>
<p class="small"><a href="data/utilization.json">Exact utilization inputs and results</a> · <a href="../h20-tilesight-memory-bound/data/board-bandwidth.json">Nominal board bandwidth source</a> · <a href="../h20-tilesight-memory-bound/data/bandwidth-calibration.json">Measured bandwidth source</a></p>
</section>'''
