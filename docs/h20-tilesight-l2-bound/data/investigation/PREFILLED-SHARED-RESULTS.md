# Prefilled shared-memory diagnostic: results and limits

**The diagnostic detects a recurring-copy effect at K2048, but it cannot assign that effect to the original kernel's unexplained time.** The modified binary is already **22.52% slower** than the original binary on identical random inputs. Its register allocation and instruction order changed. All comparisons within the diagnostic use one binary and pass exact cuBLAS correctness, but they describe this modified instruction schedule.

## What ran

The bounded session ran on `gpu-h20-4`, physical GPU 4, starting **2026-11-10 16:04:59 Singapore time**. Fourteen traced cases finished in **142.69 seconds**, below the five-minute limit. The GPU was checked idle, held under `/tmp/tom-h20-gpu4.lock`, and exposed only through its authorized UUID. Cleanup showed no remaining GPU processes; a final check showed **0 MiB, 0% utilization**. No other GPU, driver policy, or clock setting was changed.

Each case used M64 × N9984 and K512, K1024 or K2048. All cases retained:

- CTA tile 16 × 128 × 64; warp tile 16 × 32 × 64;
- 128 threads/CTA, three stages, 55,296 shared bytes/CTA;
- 312 CTAs and a measured maximum of four CTAs/SM;
- FP16 inputs/output and FP32 accumulation;
- the original warm-cache timing procedure, with 21 measured launches.

The primary time is **Nsight Systems device kernel duration**. Every traced CUTLASS launch was matched one-for-one to `launches.csv`; only rows with `phase=measure` entered the summary. CUDA-event medians are retained separately and were approximately four microseconds larger. They were not substituted for device time.

Every invocation compared all **638,976 output elements** against cuBLAS before timing. All fourteen reported **zero mismatches and zero maximum absolute error**.

## Same-binary modes

The new fixture repeats nonzero, exactly representable values along K in blocks of 64. Complete A and B allocations remain present. This permits immutable shared-memory operands without changing the result of that particular GEMM.

| Mode | Behavior |
|---:|---|
| 0 | Original pipeline in the modified binary; no extra prefill. |
| 1 | Normal recurring copies and coordination, with a common extra initialization of the third shared stage. |
| 2 | Same prefill, but recurring copies are predicated off; retain commits, waits and CTA barriers. |
| 3 | Same frozen operands; also omit recurring commits, waits and CTA barriers. Initialization and final pre-epilogue coordination remain. |

Modes 1–3 share the same initialization and binary. Mode 1 versus mode 2 tests the recurring-copy path under this schedule. Mode 2 versus mode 3 tests the remaining coordination bundle. Mode 0 versus mode 2 does not isolate a copy cost because initialization differs.

## Device-time results

All values below are medians of 21 launches, in microseconds.

| K | Mode 0 | Mode 1: normal copies + prefill | Mode 2: frozen copies | Mode 3: frozen + no recurring coordination |
|---:|---:|---:|---:|---:|
| 512 | 14.304 | 14.752 | 14.560 | 14.432 |
| 1024 | 21.856 | 22.240 | 22.048 | 21.792 |
| 2048 | 41.088 | 41.632 | 36.960 | 36.416 |

| K | Mode 1 minus mode 2 | Mode 2 minus mode 3 |
|---:|---:|---:|
| 512 | 0.192 µs | 0.128 µs |
| 1024 | 0.192 µs | 0.256 µs |
| 2048 | 4.672 µs | 0.544 µs |

At K2048, the p10–p90 ranges were 41.376–42.112 µs for mode 1, 36.896–37.024 µs for mode 2, and 36.288–36.512 µs for mode 3. The 4.672 µs copy-path difference is larger than this within-case spread. Its sharp increase between K1024 and K2048 means that one constant per-K copy cost is not supported by these three points.

For reference, the frozen modes are approximately linear over these three tested K values: descriptive slopes are 0.93314 µs/K64 for mode 2 and 0.91571 µs/K64 for mode 3. These fits describe the diagnostic only; they are not TileSight calibration constants and should not be extrapolated as a validated hardware law.

## Required baseline control: code generation materially changed

On the same GPU during the same bounded session:

| Kernel and fixture, K2048 | Device median | p10–p90 |
|---|---:|---:|
| Archived original binary, original random fixture | 33.536 µs | 33.408–33.728 µs |
| Modified binary mode 0, identical original random fixture | 41.088 µs | 40.864–41.696 µs |
| Modified binary mode 0, periodic fixture | 41.088 µs | 40.928–41.728 µs |

The new runtime-controlled binary is **7.552 µs slower**, a **22.52% increase**, before freezing any copies. The periodic fixture itself did not produce a visible median change in this mode-0 comparison.

Original binary resources: **64 registers/thread**. Modified binary resources: **72 registers/thread**, **368-byte stack frame**, zero compiler-reported spill stores/loads. Both retained 55,296 shared bytes and four-CTA maximum residency. There are local stack accesses during setup/output, so “zero spills” must not be shortened to “no local-memory traffic.” No local stack load/store was found in the recurring MMA loop.

The source reviewer also found an instruction-order change: the original binary places the final four HMMA instructions before its wait/barrier; the modified binary places them after the optional coordination block. Thus the new control did not preserve the original instruction schedule even though it preserved the algorithm and MMA/load instruction counts.

**The frozen mode is still slower than the original unmodified kernel.** This is further reason not to subtract its 4.672 µs improvement from the original measurement or declare the original residual explained.

## SASS and correctness audit

The diagnostic was compiled using CUDA 12.8 and pinned CUTLASS revision `954c8d7be60d730cc3f51e8f1ffe9850dce054d5`. The build initially failed on a duplicate CUDA constant-symbol definition. The preserved failure log documents this; the final source defines the symbol once in its pragma-once header.

The compiled recurring K64 body retains **16 HMMA and 12 LDSM instructions per warp**. Its main backedge is `0x2ab0 → 0x2340`. A uniform branch at `0x27f0` routes normal coordination through `0x2300–0x2330`, then rejoins at `0x2800`; this explains why a shorter backedge appears to contain only 12 HMMA instructions. The final four still execute after that coordination path. Conditional copy predicates and the optional coordination block remain present.

The source review checked third-stage initialization, iterator restoration, frozen-copy masks and final epilogue synchronization. All cases then passed exact mathematical checks. No dynamic HMMA/LDSM counter capture was added during this bounded session; instruction-retention evidence here is SASS plus the reviewed loop control, not a claimed hardware-counter measurement.

The clock monitor observed a 1980 MHz SM state during activity and lower states during process/trace gaps; memory clock remained 2619 MHz. Temperature was 34–36 °C. The 100 ms monitor does not measure the clock of each individual microsecond kernel.

## What this establishes

Under the modified schedule, eliminating recurring transfers changes K2048 time materially, while eliminating the remaining commit/wait/barrier bundle gives a smaller additional change. This is evidence that the transfer path and scheduling interact; the observed differences include changes in readiness, shared-memory writes, issue behavior and overlap.

It does **not** establish independent additive costs for L2, shared memory and synchronization. It does **not** establish that the original kernel's residual is caused by the same 4.672 µs. The measured code-generation perturbation is larger than that delta. The original residual remains only partly attributed by the broader investigation.

No model rate was tuned and no production or upstream kernel was changed. No further GPU work was started after the completed session.

## Published evidence

- `prefilled-shared/summary.json`: metadata, correctness and timing summaries.
- `prefilled-shared/analysis.json`: differences and descriptive fits, not calibration.
- `prefilled-shared/samples/`: all 294 measured device durations.
- `../../source/investigation/prefilled-shared/`: diagnostic source and build instructions.

Full Nsight traces, command ledgers, compiler logs and original disassembly remain in the local and remote experiment archives.
