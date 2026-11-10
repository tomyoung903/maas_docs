# Hopper TMA/WGMMA implementation control

This is a separate implementation of the same mathematical GEMM, based on the already used H20 4K-cube CUTLASS 3.x builder APIs. It is not the original 16×128×64 execution plan.

- A, B and output are FP16 and physically row-major; accumulation is FP32.
- Target shape: M=64, N=9,984, K=2,048.
- CTA tile: 64×128×64; cluster: 1×1×1.
- `KernelTmaWarpSpecialized`, explicit three stages by default.
- `NoSmemWarpSpecialized` epilogue, alpha=1, beta=0.
- No scales, quantization, bias, activation, split-K, or cooperating CTA cluster.
- Logical output grid: 1×78, with 32 K chunks. The program also reports the adapter's actual launch grid, maximum threads, shared-memory size, register count and occupancy.

Build with the pinned CUTLASS and CUDA 12.8:

```bash
CUTLASS_ROOT=/path/to/pinned/cutlass NVCC_BIN=/usr/local/cuda-12.8/bin/nvcc \
  PIPELINE_STAGES=3 bash build.sh
```

The executable is `build/stages3/benchmark`. It retains the original cache-preparation modes, read-only eviction checksum, seed-17 correctness fixture, cuBLAS comparison, warmup count, launch ledger and measured-sample CSV. Use the same environment and Nsight Systems device timing as the original kernel.

Important profiler difference: this kernel is named `cutlass::device_kernel<...>`, whereas the original uses `cutlass::Kernel<...>`. Update the Nsight filter and SQLite extraction accordingly, matching every launch to `launches.csv`. Do not assume the original 312-CTA grid, 128 threads, 55,296 shared bytes, or four-CTA residency. Read the measured metadata.

Changing from the original kernel to this kernel changes the tile size, launch grid, global-to-shared copy mechanism, MMA instruction family, warp roles and epilogue. A faster result would establish that implementation choice affects this workload. It would not validate the original 23.616 µs TileSight prediction. Any prediction comparison needs a new tile execution plan and the observed launch/residency details.

This source has received static inspection only. It must compile successfully and pass its correctness/eviction checks on the target device before its timing is used.
