# B300 DeepGEMM timing model

Fixed N6144,K1536, M1..10000, one148SM B300. GEMM-only mean of30 Nsight kernel-duration samples per shape. Quantization is excluded.

Run with Python3, numpy, scipy and matplotlib:

    python3 source/model.py --root .
    python3 source/build_report.py

The selector is adapted from DeepGEMM b4296ed; its MIT license is source/DeepGEMM-LICENSE. It matches all259 trace configurations without using latency. The timing model has3 positive fitted coefficients, calibrated by relative least squares. Fivefold validation is exploratory internal validation; no claim of untouched test data or transfer to otherN,K/hardware is made. See source/derivation.md and rendered report for methodology and limits.

measurements.json contains both sweeps'30 per-kernel timings and observed configuration per shape, with input-source SHA256 hashes. model.json records all fit metrics, fold predictions/coefficients and shape-level predictions. predictions.csv is the compact numerical result. No GPU or network is required to reproduce analysis.
