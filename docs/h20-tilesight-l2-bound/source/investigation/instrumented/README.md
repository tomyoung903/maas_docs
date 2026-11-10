# Diagnostic CTA phase timestamps

This is a paired build of the archived `16×128×64`, three-stage CUTLASS kernel. Mathematical work and correctness checks are unchanged. The overlay header comes from the exact archived CUTLASS checkout, not a current upstream revision.

```bash
CUTLASS_ROOT=/path/to/pinned/cutlass NVCC_BIN=/usr/local/cuda-12.8/bin/nvcc \
  ENABLE_PHASE_TRACE=0 bash build.sh
CUTLASS_ROOT=/path/to/pinned/cutlass NVCC_BIN=/usr/local/cuda-12.8/bin/nvcc \
  ENABLE_PHASE_TRACE=1 bash build.sh
```

Outputs are `build/trace0/benchmark` and `build/trace1/benchmark`. Run them with the same input and cache preparation under Nsight Systems. Preserve the compiled register counts, occupancy, and measured times for both. Do not assume instrumentation has zero cost.

When tracing is enabled, thread 0 of every valid CTA reads `%globaltimer` at four locations:

1. Entry to the GEMM kernel operator.
2. Immediately before calling the threadblock MMA operator.
3. Immediately after the threadblock MMA operator returns.
4. Immediately after the epilogue operator returns.

Timestamps stay in thread-local variables until the final location. Thread 0 then writes one 48-byte diagnostic record. No new CTA barrier is inserted. The trace buffer is allocated and initialized outside measured intervals. All GEMM launches update the buffer, so `cta-phases.csv` records the final measured launch. The CSV includes that launch's index from `launches.csv`, CTA coordinates and SM ID. The four fields are nanoseconds from `%globaltimer`, with its hardware timer granularity; differences are not cycle counts.

Use `python3 analyze_phases.py /path/to/cta-phases.csv --output phases-summary.json` for per-phase distributions and actual CTA placement. The script never labels the CTA envelope as the profiler's kernel duration.

The MMA region includes its own prefetch, shared-memory reads, repeated MMA instructions, waits, barriers and draining. It does not isolate Tensor Core active time. The epilogue region includes iterator setup, shared-memory reordering, conversion and output stores. The end timestamp is thread 0's observation before diagnostic writes and before kernel completion; it is not a completion fence for all warps or stores.

These values are diagnostic evidence. Register pressure, scheduling, code layout, conditional execution and the final stores can change the measured kernel. Compare trace-on and trace-off timings first. Do not subtract instrumented phase values directly from uninstrumented timing or call the difference an exact root-cause decomposition.
