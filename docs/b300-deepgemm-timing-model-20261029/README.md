# B300 DeepGEMM timing model

Fixed N6144,K1536, M1..10000, one148SM B300. GEMM-only mean of30 Nsight kernel-duration samples per shape. Quantization is excluded.

Run with Python3, numpy, scipy and matplotlib:

    python3 source/model.py --root .
    python3 source/build_report.py

The selector is adapted from DeepGEMM b4296ed; its MIT license is source/DeepGEMM-LICENSE. It matches all259 trace configurations without using latency. The timing model has3 positive fitted coefficients, calibrated by relative least squares. Fivefold validation is exploratory internal validation; no claim of untouched test data or transfer to otherN,K/hardware is made. See source/derivation.md and rendered report for methodology and limits.

measurements.json contains both sweeps'30 per-kernel timings and observed configuration per shape, with input-source SHA256 hashes. model.json records all fit metrics, fold predictions/coefficients and shape-level predictions. predictions.csv is the compact numerical result. No GPU or network is required to reproduce analysis.

gemm-time-and-utilization.svg/png adds a right-hand utilization axis to the original full-range timing plot. Each point is 100 * (2*M*N*K) / (mean_GEMM_time_seconds * 4.5e15). NVIDIA's HGX B300 table lists 72 PFLOP/s sparse FP8 for eight GPUs and says dense is half: 72/2/8 = 4.5 PFLOP/s dense FP8 per GPU (https://www.nvidia.com/en-us/data-center/hgx/, verified 2026-10-30). This is a nominal peak reference, not a hardware activity counter or a calibrated sustained peak. predictions.csv and model.json include useful_gemm_flops, achieved_tflops, and compute_utilization_pct. Mean time includes the complete GEMM kernel; the numerator counts only useful 2MNK FLOPs.

The green HBM curve is the explicitly assumed logical-payload bandwidth: (M*K + N*K + 2*M*N) / mean_GEMM_time_seconds, divided by the 7.7e12 B/s nominal single-HGX-B300 HBM peak, then multiplied by100. Each FP8 input is read once from HBM per call; each BF16 output is written once; prior output is not read. This permits input reuse within one GEMM but none across calls. Scale metadata, padding, transaction granularity and repeated fetches are excluded. Existing measured timings are reused, so this does not measure physical HBM traffic or predict cold-cache runtime. NVIDIA source: Blackwell Ultra datasheet page5, https://dam-cdn.nvd.orangelogic.com/AssetLink/1k0p832eq8r5ca0u5383ie5o4tp3bst1.pdf (verified2026-10-30). CSV and JSON include separate read/write/total byte counts, assumed_hbm_tb_s and assumed_hbm_utilization_pct.
