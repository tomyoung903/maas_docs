# Independent H20 memory-rate recheck

**The new measurements do not support reducing this GEMM's L2 rate by approximately 30% simply to close its timing gap.** A warm `cp.async` control with 312 CTAs reaches **7.906–8.026 TB/s**, close to TileSight's stored **8.123448629 TB/s**. The repository's simpler global-to-register probe reaches only **5.686–5.727 TB/s**. These are different instruction streams and must not be treated as interchangeable measurements of one hardware constant.

A separate concrete defect was found in the repository's shared-memory probe: CUDA 12.8 collapses repeated shared loads. Its nominal **384–386 B/cycle/SM** result is invalid. An isolated control that makes the PTX load volatile retains every load and measures **127.55–127.73 B/cycle/SM**. That is useful evidence for this read primitive. It is not an all-SM mixed read/write calibration.

## Scope and execution

- Run started **2026-11-10 15:41:44 Singapore time** on `gpu-h20-4`, physical GPU 4.
- GPU was checked idle before each session. Both sessions held `/tmp/tom-h20-gpu4.lock` and exposed only the selected GPU through `CUDA_VISIBLE_DEVICES`.
- First session: 20 commands, **21.21 seconds**. Shared-load control: nine commands, **8.75 seconds**. All completed successfully. Both cleanup records show no remaining GPU processes. Final read-only check showed **0 MiB and 0% utilization** on the selected GPU.
- No GPU clocks, power limits, driver policy, existing services, or other GPUs were changed. No rental was used.
- CUDA **12.8**, `-O3 -DNDEBUG -arch=sm_90a -lineinfo`. Complete compile commands are in `memory-rate-recheck/source/build.sh` and the original command lists in each `intent.json`.
- Local checkout: `work/tilesight-h20`, commit `6673bc3941d23572caad5d25473c9f129c3f000a`. The three original probe files match that checkout byte for byte. Their last source commit is the upstream initial commit `75428c41b7a1127497151a3db4316a1223d342cf`.
- Only copied diagnostic files were changed. The TileSight checkout remains clean.

## Repository L2 probe

`core l2` reads a **30 MiB** footprint, half the device's reported **60 MiB L2**. It launches **312 CTAs × 256 threads**. Each thread loads one 16-byte vector per source iteration with `ld.global.cg.v4.u32`, then accumulates four integer checksums. The address uses a modulo operation. A final checksum store is outside the byte numerator but inside the timed kernel. Three warmups precede seven CUDA-event samples; the executable reports their median.

The counted read bytes are:

`312 × 256 × iterations × 16`.

The compiled kernel uses 34 registers/thread, no shared memory, and has a maximum residency of six CTAs/SM. The actual grid supplies four CTAs/SM on average. SASS retains the global loads. Its main loop has four `LDG.E.128.STRONG.GPU` instructions for four source iterations.

Each row below summarizes three separate commands, each itself reporting the median of seven timings:

| Iterations | Median of command medians, TB/s | Minimum | Maximum | Stored L2 rate |
|---:|---:|---:|---:|---:|
| 4096 | 5.686500 | 5.682944 | 5.687489 | 8.123449 |
| 8192 | 5.726513 | 5.726012 | 5.726614 | 8.123449 |

This probe measures the throughput of its global-to-register loop, including address calculations and checksum arithmetic. It does not measure the GEMM's global-to-shared `cp.async` path. A cache-sized footprint and warmups are not hardware-counter proof that every access hit L2.

## Warm-cache path controls

The existing `dram_sweep` program was invoked directly with **16 MiB and 32 MiB** input footprints. Its power-of-two restriction prevents using 40 MiB without modifying the program. Both chosen footprints are below the reported 60 MiB L2.

All controls use 128 threads/CTA, eight 16-byte requests/thread/iteration, 4096 iterations, and seven timed samples. An untimed complete warmup precedes every sample. All reported sampled checksum validations passed. These are sampled checks, not exhaustive output validation.

- **`read_cg`:** `ld.global.cg.v4.b32` into registers, then checksums. A 54 KiB shared-memory guard limits maximum residency to four CTAs/SM.
- **`cp_async`:** eight `cp.async.cg.shared.global` requests, commit, wait for all copies, CTA barrier, shared-memory checksum reads, then another CTA barrier. A 38 KiB guard plus 16 KiB operand buffer gives the same **55,296 bytes/CTA** and four-CTA maximum residency.
- The read numerator is `blocks × 128 × 4096 × 8 × 16` bytes. It excludes checksum stores and does not add shared-memory bytes to the numerator.
- SASS verifies eight `LDGSTS.E.BYPASS.128` instructions, one commit, one wait and two CTA barriers in each `cp_async` iteration. The `read_cg` main loop retains 16 loads for two source iterations, plus eight for a remainder.

| Footprint | CTAs | `read_cg` median TB/s | `cp_async` median TB/s |
|---:|---:|---:|---:|
| 16 MiB | 78 | 1.791005 | 3.513119 |
| 16 MiB | 156 | 3.535022 | 6.313066 |
| 16 MiB | 312 | 6.736173 | 8.025505 |
| 32 MiB | 78 | 1.165541 | 2.689275 |
| 32 MiB | 156 | 2.439603 | 5.098345 |
| 32 MiB | 312 | 4.916677 | 7.906418 |

For 312 CTAs, the seven-sample ranges are:

| Footprint/path | Minimum TB/s | Median TB/s | Maximum TB/s |
|---|---:|---:|---:|
| 16 MiB, `read_cg` | 6.730076 | 6.736173 | 6.739364 |
| 16 MiB, `cp_async` | 8.020488 | 8.025505 | 8.033388 |
| 32 MiB, `read_cg` | 4.898787 | 4.916677 | 4.920523 |
| 32 MiB, `cp_async` | 7.883270 | 7.906418 | 7.968039 |

The 312-CTA `cp_async` results are **1.21% and 2.67% below** the stored 8.123448629 TB/s value. They make a large universal downward correction difficult to justify. They do not prove the GEMM sustains this rate: it has a different access pattern, arithmetic, shared-memory demand, scheduling and finite duration.

**The `cp_async` control is a combined-path measurement.** Its time includes copy waits, barriers and checksum reads. It must not replace the L2 port rate in a model that also charges for those same costs. The CSV calls its output `achieved_ddr_bw_*`; for these warm, cache-sized runs, that label does not establish HBM bandwidth. We report warm-path throughput instead. No hardware cache-hit counters were obtained in this recheck.

## Shared-memory probe: confirmed compiler defect and isolated correction

The original `core smem` source launches **one CTA of 256 threads**, with 4096 bytes of shared data. The generic stdout header incorrectly suggests 312 blocks; the launch itself is one block. Each thread initializes its own 16-byte shared vector before the timer, then repeatedly loads it and sums its four words. Thread 0 records `clock64` elapsed cycles after an ending CTA barrier. The numerator is `256 × iterations × 16` bytes. Two warmups precede seven samples.

CUDA 12.8 compiled the original PTX `ld.shared.v4.u32` as follows:

- Dominant loop: branch `0x710 → 0x4e0`; counter decreases by 16, but the loop contains **one** `LDS.128` and 16 checksum updates.
- Four-iteration and one-iteration remainder loops also reuse loaded values; for example `LDS.128` at `0x970` is outside the backedge to `0x980`.

The benchmark therefore counts reads that the compiled kernel does not perform. `asm volatile` in CUDA C++ did not prevent this PTX-level optimization.

The isolated control changes exactly one instruction spelling:

```diff
- ld.shared.v4.u32
+ ld.volatile.shared.v4.u32
```

Its main backedge `0x800 → 0x4e0` contains **16 `LDS.128` instructions for 16 source iterations**. Remainder loops also retain each required load. The source and its SASS are preserved separately in `memory-rate-recheck/volatile-control/`.

| Iterations | Original reported B/cycle/SM — INVALID | Volatile control B/cycle/SM |
|---:|---:|---:|
| 4096 | 384.622100 | 127.551383 |
| 8192 | 386.198057 | 127.725201 |

All three command medians were identical within each row and variant. The correction removes an actual compiler flaw; it was not adjusted to match a GEMM time.

The valid control includes checksum arithmetic and the ending barrier. It measures a read-only primitive on one SM. There are distinct addresses per lane, so this is not a same-address warp broadcast. It does not measure `ldmatrix`, simultaneous `cp.async` writes, mixed reads/writes, or aggregate throughput across 78 SMs.

The stored shared-memory value is **19.768320312 TB/s**. This recheck supplies no direct aggregate replacement for it. For orientation only, `128 B/cycle × 1.98 GHz × 78 = 19.76832 TB/s`; that arithmetic is an extrapolation, not a new measured aggregate result. The valid per-SM read result is close to the 128 B/cycle factor, but that does not validate every use of the aggregate constant.

## Clocks, interpretation and evidence

The monitor observed SM clocks of 345 MHz when idle and 1980 MHz during activity; memory clock stayed at 2619 MHz. Independent `clock64/globaltimer` probes gave command medians of **1.979889–1.979938 GHz** in the first session and **1.979879–1.979994 GHz** in the control session. Clock settings were unchanged. This recheck was on gpu-h20-4; it does not retrospectively prove that previous gpu-h20-5 runs had identical operating conditions.

These results separate two findings:

1. A model must match its rate to the instruction family and execution path. The simple L2 probe's lower result does not justify substituting that number for `cp.async` GEMM traffic.
2. Calibration programs themselves need SASS checks. This shared-memory probe can silently count removed loads. Its original output must be rejected before any profile update.

This diagnostic neither modifies the TileSight profile nor fits any rate to the GEMM measurement. It narrows the explanation: a blanket 30% L2 correction is not supported by the closer-path control, and the shared primitive is near 128 B/cycle after correcting the compiler flaw. The remaining GEMM timing difference still requires execution-plan and instruction-scheduling evidence.

Evidence in this page's download:

- `data/investigation/memory-rate-recheck/summary.json`: measurements and validity labels.
- `data/investigation/memory-rate-recheck/runs/`: raw benchmark stdout.
- `source/investigation/memory-rate-recheck/`: original and corrected sources, disassembly and reproduction commands.

Full local run ledgers and device metadata remain in the experiment archive.
