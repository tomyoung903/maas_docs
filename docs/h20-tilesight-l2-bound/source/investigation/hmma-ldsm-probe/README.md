# Independent HMMA plus shared-operand probe

This probe compares register-only HMMA with the same arithmetic plus explicit shared-memory operand reads. It contains no measured GEMM duration and does not fit an H20 rate to the target kernel.

The archived CUTLASS SASS has, per warp per K16 fragment, one `LDSM.16.M88.4`, two `LDSM.16.MT88.4`, and four `HMMA.16816.F32`. For example, addresses 0x1a80 through 0x1bf0 show HMMA0; next-fragment A and B0 reads; HMMA1; next-fragment B1 read; then HMMA2 and HMMA3. The source is `outputs/h20-l2-bound-20261110/source/kernel.sass`. This probe matches those instruction families and counts.

Three controls share the same four independent FP32 accumulator groups:

- `pure`: four MMA instructions using register operands.
- `pipelined`: ping-pong register fragments, with the three next-fragment `ldmatrix.x4` reads interspersed with the current four MMA instructions.
- `serial`: three operand reads followed by four MMA instructions. This is a scheduling counterfactual, not the CUTLASS schedule.

The default launch is 312 CTAs of 128 threads on a 78-SM H20. Every variant requests 55,296 dynamic shared bytes, matching the original kernel's four-CTA residency cap. Eight physical 6,144-byte chunks contain operand data (49,152 bytes total). Within each chunk, each warp has a 512-byte A fragment and two 512-byte B fragments. The load chunk is `(outer_iteration + unrolled_round) & 7`, so every round has a different address and the rotation changes between outer iterations. Contiguous aligned 8×8 matrix rows give a simple bank-friendly layout. It does not reproduce CUTLASS's exact shared-memory swizzle or global-memory pipeline.

All input elements are exactly FP16 0.125. Each MMA adds exactly 0.25 to each accumulator. All 16 FP32 outputs per thread are retained and checked on the CPU. Shared memory is initialized before the thread-0 loop timestamp. The pipelined variant also preloads its initial operand fragments before that timestamp. Both mixed variants perform exactly three `ldmatrix.x4` loads per four MMA instructions within the loop. The final pipelined loads prepare an unused next fragment, preserving the steady-state instruction count.

CUDA events measure the entire kernel, including initialization and final stores. The default two long loop lengths, 4,096 and 8,192 outer iterations with eight unrolled rounds each, make those fixed costs small and test convergence. Device timestamps additionally record thread 0's loop interval and SM ID for each CTA. They are diagnostics, not a substitute for a whole-kernel profiler interval.

Build and run on an independently checked idle GPU:

```sh
NVCC_BIN=/usr/local/cuda-12.8/bin/nvcc bash build.sh
CUDA_VISIBLE_DEVICES=<device-uuid> ./probe \
  --modes pure,pipelined,serial --blocks-per-sm 4 \
  --iterations 4096,8192 --repeats 7 --warmup 3
```

All samples go to `probe-samples.csv`. Per-CTA loop records from the final sample go to `phases-<mode>-<iterations>.csv`. JSON output reports actual registers, spills, shared memory, occupancy, arithmetic counts and timing. Inspect compiled SASS for the expected HMMA/LDSM count and reject spilled configurations from a throughput comparison.

Per outer iteration, every warp executes 32 HMMA instructions and, for mixed modes, 24 LDSM instructions. Each HMMA is 4,096 FLOPs; each `ldmatrix.x4` reads 512 logical operand bytes across the warp. Thus:

`FLOPs = grid_blocks × 4 warps × 4 HMMA × 8 unroll × iterations × 4096`

`Shared operand bytes = grid_blocks × 4 warps × 3 LDSM × 8 unroll × iterations × 512`

The mixed result is an **instruction-mix throughput**, not a generic Tensor Core peak. The difference from `pure` tests operand loading and its dependency/issue coupling. It does not include `cp.async`, full iterator arithmetic, CTA barriers, prologue/epilogue, cold HBM traffic, or the exact CUTLASS shared layout. Do not add its slowdown blindly to an existing model if that model already prices the same shared traffic.

## V2: prevent assembler load hoisting

The first version repeatedly loaded identical shared addresses. CUDA 12.8 ptxas hoisted/reused those loads despite volatile inline PTX, producing only three serial or six pipelined static LDSM instructions instead of 24 per eight-round loop. That source and its known artifacts are preserved in `v1-hoisted-loads/` and must not be used as a matched instruction-mix rate.

Version2 rotates through eight physical shared chunks with an outer-loop-dependent address. All chunks contain the same exact FP16 values, so every accumulator still has the same exact reference. Shared initialization of all49,152 bytes remains before the loop timestamp and is identical across controls. The pipelined stream consumes the previously prefetched chunk; the serial stream consumes the current chunk. This changes no operand value because all chunks are identical.

Before using version2 rates, confirm the actual compiled main loop has32 HMMA and24 LDSM instructions per eight-round body in each mixed variant. The pipelined variant additionally has three prologue LDSM instructions outside the loop. If that check fails, do not use the result as an instruction-mix calibration.
