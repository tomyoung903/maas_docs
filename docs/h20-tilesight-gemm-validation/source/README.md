# Reproduce the H20 GEMM comparison

This bundle uses one H20 GPU. Confirm that the GPU is available and authorized for use before running the benchmark.

Requirements: CUDA 12.8 with nvcc and cuBLAS, an H20-compatible driver, Nsight Systems (`nsys` on PATH), Python 3.10 or newer, and a C++17 toolchain.

Prepare pinned dependencies in your preferred working directory:

```bash
git clone https://github.com/tomyoung903/TileSight.git
git -C TileSight checkout 71c51b223230b4bc13cfcaf3cb1ca25363e6ffb9
git clone https://github.com/NVIDIA/cutlass.git
git -C cutlass checkout 954c8d7be60d730cc3f51e8f1ffe9850dce054d5
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ./TileSight
export CUTLASS_ROOT="$PWD/cutlass"
```

Extract the source bundle into a separate experiment directory and change into it. Keep the virtual environment active and `CUTLASS_ROOT` set to the dependency checkout.

```bash
bash build.sh
CUDA_VISIBLE_DEVICES='' HIP_VISIBLE_DEVICES='' ROCR_VISIBLE_DEVICES='' \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python predict_suite.py
python run_suite.py
python collect_results.py
```

The build uses `nvcc` on PATH by default; `NVCC_BIN` can select a specific CUDA compiler. The runner checks physical GPU 0 for compute processes before starting each measurement. It takes a cooperative per-user lock, limits subprocess duration, and stops its clock logger when each run ends. It does not reserve the GPU for other users or replace your resource-allocation policy.

`cases.json` fixes all five shapes. The model runs before measurement, uses one CTA per SM, and retains the repository's H20 timing constants. The benchmark uses FP16 inputs/output, FP32 accumulation, 128 × 128 × 64 tiles, and three pipeline stages. cuBLAS checks numerical correctness outside timing.

Each case directory contains model snapshots, correctness results, CUDA-event timings, clock samples, an Nsight report, a SQLite export, and extracted device durations. `comparison.csv` and `comparison.json` combine the results. The trace extractor expects 203 ordinary CUTLASS launches: one correctness check, 100 warmups, 51 repeated-input measurements, and 51 cold-prepared measurements. Default Nsight graph tracing does not expose individual graph-node durations in this extraction.

The archived measurements were collected with CUDA 12.8 on an H20 with 78 SMs. Observed clocks under load were 1,980 MHz. Differences in hardware state, toolchain, driver, or competing activity can change the measured values. Do not adjust model parameters merely to reproduce the published agreement.
