# GLM-5.2 FP8 B=500 DP8/EP8 decode profile

- Cluster: `prod-maas-h200-jp`
- Namespace: `maas-dev-tom`
- Candidate node: `gpu-h200-36`
- Hardware: 8 NVIDIA H200 GPUs
- Model: `/home/models/zai-org/GLM-5.2-FP8`
- Runtime image: `image.hpc-ai.com/platform/dynamo-sglang-runtime@sha256:8fa3a4c397860756070300e9adab901abd0098a34ac7bfff13ae0be20b789f8b`
- Topology: TP=8, DP=8, EP=8, PP=1
- DP attention: enabled
- Expert transport: DeepEP low-latency mode
- Speculative decoding: disabled
- Transfer backend: fake decode handoff
- Global native batch: 500 sequences
- Requested context: 4,096 tokens per sequence
- Effective context: 3,072 tokens per sequence
- Context adjustment reason: runtime profiling capped each DP lane at 200,000 KV tokens; 4,096 tokens cannot fit 63 local requests
- Output contract: two returned tokens per sequence, comprising one fake handoff token and one GPU-computed decode token
- Requested KV pool cap: 460,800 token slots per local worker
- Effective runtime-profiled KV pool cap: 200,000 token slots per DP lane
- Page size: 64 tokens
- Reserved decode tokens: 16 per request
- Worst local attention batch: 63 sequences
- Conservative local KV requirement at 3,072 context: 197,568 token slots (`63 * ceil((3072 + 16) / 64) * 64`)
- Decode CUDA Graph shape: local batch 63
- Capture: Nsight Systems, CUDA graph node tracing, CUDA profiler API range
- Required result evidence: HTTP 200; 500 unique RIDs; 500 prompt-token counts of 3,072; 500 completion-token counts of two; zero prefill rows; one useful computed decode generation; all eight ranks present
- Audit: unique semantic ownership, per-device interval union, overlap excess, representative layer/rank boundary checks, MFU/MBU numerator-denominator consistency
- Publication target: `https://tomyoung903.github.io/maas_docs/tmp/basic-kernel-understanding-japan-tp8-decode-batch-sweep-4k/`

Fake transfer allocates the requested context shape without transferring semantically correct prompt KV. This experiment compares decoder execution structure and kernel timing; it is not a correctness benchmark.
