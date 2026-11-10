# Independent register-only HMMA throughput probe

Purpose: test the sustainable rate of the **actual instruction family used by the narrow CUTLASS kernel**, independently of its measured time. The existing139.22TFLOP/s model constant may come from a different MMA family. This experiment does not infer a rate by dividing GEMM FLOPs by GEMM duration.

The inner instruction is exactly:

`mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32`

Each warp instruction computes16×8 outputs overK16: **2×16×8×16=4096FLOPs perwarp instruction**. The existing CUTLASS SASS uses `HMMA.16816.F32`; verify the probe's compiled SASS also maps one PTX instruction to one such SASS instruction before using the rate. This is not an old Volta HMMA step-count calculation.

## Probe design

- Entire main loop is register-only; no global or shared operand loads.
-1,2,4,8,16 independent accumulator groups perwarp test instruction-level parallelism.
-128- and256-thread blocks and1,2,4,8 blocks perSM in the grid test warp supply. A configuration exceeding its occupancy capacity is explicitly skipped, rather than accidentally timing multiple waves.
- Runtime register count, local memory/spill size, occupancy cap and shared allocation are reported. Discard spilled cases from instruction-throughput calibration, but retain their raw results.
- Eight unrolled rounds per outer iteration reduce loop/control overhead. The default4096/8192 iteration pair tests long-loop convergence.
- Each of six operand registers comes from a separate kernel argument. The host supplies the same bits to all six, but compiler dataflow cannot assume argument equality. This avoids compiling the inputs down to one known-equal constant register. SASS should still be inspected.
- Constant half inputs A=B=0.125 give exactly+0.25 per FP32 output perMMA. Each group's final value is `iterations*8*0.25`, independent of group count. The allowed iteration range keeps quarter-unit accumulation exact and finite.
- Every accumulator is written once at the end, in a coalesced structure-of-arrays layout, then checked on theCPU before timing. All output entries must match exactly. Volatile inline PTX prevents arithmetic elimination.
- CUDA events enclose the kernel only; seven samples and three untimed warmups bydefault. Store and launch overhead remain included. No overhead is subtracted to create a favorable rate. Their relative effect should shrink at the longer loop length.
- There is no GEMM shape or measured GEMM time in this program.

This is deliberately favorable to register reuse. It calibrates an instruction-family ceiling, not the full GEMM pipeline with shared loads, address arithmetic and synchronization.

## Build and run

Compile without accessing aGPU:

```sh
NVCC_BIN=/path/to/cuda-12.8/bin/nvcc bash build.sh
/path/to/cuobjdump --dump-sass probe >probe.sass
```

The parent must select and verify an idle GPU and preserve the same isolation/monitoring rules as the existing experiment. Mask that one device; the program uses device0 within the mask. Start with the baseline's practical warp supply:

```sh
CUDA_VISIBLE_DEVICES=<selected-device> ./probe \
  --groups 1,2,4,8,16 --threads 128 --blocks-per-sm 4 \
  --iterations 4096,8192 --repeats 7 >probe-matched.jsonl
```

Full independent sweep, in a separate output directory because the raw CSV is written to the current directory:

```sh
CUDA_VISIBLE_DEVICES=<selected-device> /path/to/probe \
  --groups 1,2,4,8,16 --threads 128,256 --blocks-per-sm 1,2,4,8 \
  --iterations 4096,8192 --repeats 7 >probe-full.jsonl
```

The program writes all individual event samples to `probe-samples.csv`, plus oneJSON object per configuration tostdout. Metadata and skipped configurations are also retained.

For every run:

`warp_MMA_count = grid_blocks * (threads_per_block/32) * groups * 8 * iterations`

`FLOPs = warp_MMA_count *4096`

`TFLOP/s = FLOPs / measured_microseconds /1e6`

## Interpretation

Look for a rate plateau as independent accumulator groups and warp supply increase. Check that doubling loop length gives a similar rate and that no local-memory spills appear. Use the complete sweep, not only the fastest sample. Compare the plateau with both139.22TFLOP/s and the original kernel's apparent rate. If these differ, that motivates a **path-specific calibration** rather than replacing every H20 tensor instruction family with one new number.

A change to the GEMM prediction based on this independent result is a calibrated prediction. Validate it on held-out shapes/loop lengths and label it separately from the original upstream profile.
