# Taiguo GB300 TP-only decode and kernel-sweep contract

## Full-model B=100 capture

- Cluster: `prod-maas-gb300-taiguo`; namespace: `maas-dev-tom`.
- Hardware: one TP=8 replica spanning four GB300 GPUs on
  `gpu-master-gb300-132` and four on `gpu-worker-gb300-192`.
- Model: `/mnt/HPC/models/zai-org/GLM-5.2-FP8`.
- Runtime image: `image.hpc-ai.com/platform/dynamo-sglang-runtime:284b969e-dev-before-v0.5.14-sync-20260709-168610be-arm64`.
- Runtime source: the live deployment's `/mnt/HPC/siqin/sglang` checkout,
  mounted read-only; its Git revision, dirty-file list, and patch are captured
  beside the trace.
- Model loading: ordinary `safetensors`. The first `fastsafetensors` attempts
  failed before capture because GDS is unavailable on worker 192 and the
  no-GDS fallback addressed global TP rank 4 as a local CUDA ordinal. This
  startup-only substitution does not alter the checkpoint tensors or captured
  decode kernels.
- Topology: TP=8, DP=1, EP=1, PP=1. DP attention and expert parallelism are
  disabled even though the live production deployment uses DP=8 and EP=8.
- Decode mode: standard autoregressive decode with no speculative algorithm.
- Decode isolation: fake disaggregated handoff, matching the H200 native B=100
  experiment.
- Logical request: one native batched `/generate` call containing 100 distinct
  sequences, each with 4,096 deterministic token IDs and `max_new_tokens=2`.
  The pre-capture expectation was one fake-handoff token and exactly one
  computed decode forward.
- KV cache: FP8 E4M3, page size 64, 16 reserved decode tokens, and at least
  460,800 total token slots.
- CUDA graph: exact B=100 capture only; the measured request must report
  `real_bs=100`, zero prefill rows, and no speculative kernels.
- Capture: Nsight Systems CUDA/NVTX/OSRT with CUDA graph node tracing and
  CUDA-profiler API range control, independently on both nodes.

The hardware, runtime revision, and backend kernels differ from the H200
experiment. Only the logical request and TP-only model contract are aligned.
Cross-hardware ratios must never participate in the H200 B=1 scaling identity.

### Post-capture contract audit

The response payload proves two output IDs per sequence, but the captured
request contains two complete, implementation-equivalent, eight-rank CUDA
graph replays and both finish before the latest matched request `Finish`
boundary. The response exposes no per-token timestamps, the scheduler log is
coarse, and CUDA graph correlation IDs contain no token ordinal. Consequently,
the exactly-one-computed-forward expectation **fails validation**: neither
replay may be labeled fake-handoff, token 1, token 2, or cleanup from the
available evidence. The analysis tree uses the explicit label **selected
representative first/longer CUDA-graph replay**; the second replay is preserved
as **alternate complete CUDA-graph replay; token role unassigned**.

This differs materially from the H200 reference capture: there, the second
graph crossed the matched `Finish` boundary, which supplied evidence for its
cleanup/steady-body label. That H200 label is not transferred by ordinal to
GB300.

## Standalone kernel-efficiency sweep

- Node: `gpu-master-gb300-139`; one GB300 is requested for per-rank compute
  kernels. TP collective controls may use the full-model pair after its server
  exits.
- Batch sizes: B = 1, 10, 20, 100, 200, and 500.
- Each case uses TP=8 per-rank shapes and the same dtypes/layouts selected by
  the B=100 GB300 runtime.
- Every benchmark records warmups, repeated latency samples, exact tensor
  shapes, logical FLOPs or useful-byte floor, kernel symbols, and profiler
  provenance. MBU is a modeled useful-byte floor unless a hardware DRAM
  counter is explicitly captured.
- The standalone B=100 median is compared with the matching logical operation
  in the full-model B=100 capture. A mismatch is reported rather than hidden.

## Safety and lifecycle

Kubernetes initially showed no GPU-requesting pods on nodes 130, 132, 139, and
192. Host-level inspection then rejected node 130 because a developer Docker
container exposed all GPUs and an EGM NVLink loopback process held GPU 0. Node
192 still hosted a CPU/RAM-heavy Mooncake client but its four GPUs were idle;
nodes 132/139 are schedulable control-plane nodes. The full TP job therefore
used the four host-verified idle GPUs on node 132 plus the four host-verified
idle GPUs on worker 192, while the bounded standalone sweep used only GPU 0 on
node 139. Node 130 was not used.
Each GPU pod performs an in-container `nvidia-smi` compute-process gate before
starting work. All experiment pods have finite deadlines and must be removed
after artifacts are copied and verified.
