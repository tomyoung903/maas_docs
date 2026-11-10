# Same-binary prefilled shared-memory diagnostic

This diagnostic retains the original CTA 16 × 128 × 64, warp 16 × 32 × 64, 128 threads,
three stages, and FP16 inputs/output with FP32 accumulation. One runtime selector
controls the modes. All modes therefore use the same compiled kernel resources.

Build with the exact pinned CUTLASS checkout and CUDA 12.8:

```sh
CUTLASS_ROOT=/home/tom/experiments/single-cta-b300-20261105/kernel/deps/cutlass \
NVCC_BIN=/usr/local/cuda-12.8/bin/nvcc bash build.sh
```

The CLI remains `build/benchmark M N K`. K must be at least 192 and divisible by 64.
Select `PREFILL_DIAGNOSTIC_MODE`:

| Mode | Meaning |
|---:|---|
| 0 | Original pipeline on the selected fixture; no extra prefill. |
| 1 | Normal recurring copies/waits/barriers, with an extra common third-stage prefill and full initial wait. |
| 2 | Same prefill; clear global iterator masks so recurring copies are predicated off. Retain recurring commits/waits/barriers. |
| 3 | Same frozen operands; omit recurring commit/wait/CTA barrier. Retain full initialization and final pre-epilogue wait/barrier. |

Modes 1–3 require the new K64-periodic fixture. Each element is a nonzero multiple
of 1/8 from -1 to 1. The first 64 K positions vary by row/column; only the K64 slices
repeat. The complete original-sized A/B allocations remain present, and every
mode checks every output against cuBLAS outside timing. This is not the original
random-data workload.

Optional `PREFILL_RANDOM_FIXTURE=1` selects the original `mt19937(17)` fixture,
and is accepted only in mode 0. This provides an instrumented-binary comparison
with the archived random-data baseline. The mode and fixture are printed.

Example run (parent must select an idle GPU, hold the cooperative lock, and keep
the complete GPU session below five minutes):

```sh
PREFILL_DIAGNOSTIC_MODE=2 CACHE_CONTROL_MODE=warm CACHE_CONTROL_REPEATS=21 \
  build/benchmark 64 9984 2048
```

Each invocation writes `launches.csv` and `samples.csv` in its current working
directory. Run modes in separate directories. Nsight kernel records must align
with `launches.csv`, and only `phase=measure` belongs in the device-time summary.

The overlay comes from pinned `mma_multistage.h`. After the original prologue,
it fills the third stage using temporary global iterators and restores the
shared write iterators. It does not advance the original K count or ring indices.
The extra prefill is common to modes 1–3. For frozen modes, `kNone` predication
leaves shared memory unchanged; it does not zero-fill invalid copies.

Validate correctness, shared allocation, register count, occupancy, and retained
HMMA/LDSM instructions before interpreting timings. Per K64, expect 16 HMMA and
12 LDSM instructions per warp. Verify optional copy/barrier predicates in SASS.
No compiler-eliminated memory work may be counted as performed work.

Mode 1 versus mode 2 tests the recurring operand-transfer path in the mixed loop.
Mode 2 versus mode 3 tests remaining coordination with immutable operands. Neither
difference is an additive cost of the original random-data kernel. Mode 0 versus
mode 1 measures the changed diagnostic initialization, not a removed memory cost.

## Compiled control limitations

CUDA 12.8 reports 72 registers per thread and a 368-byte stack frame, with no
register spill stores or loads. Stack accesses occur in setup/output, outside
the repeated main loop. The unchanged shared allocation should still limit
residency to four CTAs per SM; runtime metadata must confirm this.

The main K64 backedge is `0x2ab0 → 0x2340`. It contains all 16 HMMA and 12 LDSM
instructions. The conditional branch at `0x27f0` visits the coordination block
at `0x2300–0x2330` and rejoins at `0x2800`, before the final four HMMA instructions.
The original compiled kernel placed those final four HMMA instructions before
its wait/barrier. Thus instruction counts and warp geometry are preserved, but
the compiler's scheduling is not identical. The original-binary versus modified
mode 0 random-fixture timing is required to show the disturbance. Diagnostic
mode differences cannot be transferred directly to the original kernel.

Published source and CSV copies normalize line endings and trailing whitespace. Exact run files remain in the experiment archive. This diagnostic perturbed its unchanged baseline by22.52%; its timing deltas are not an attribution of the original kernel residual.
