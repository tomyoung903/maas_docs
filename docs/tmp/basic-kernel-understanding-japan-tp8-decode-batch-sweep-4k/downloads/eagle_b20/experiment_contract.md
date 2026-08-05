# Japan H200 TP=8 EAGLE B=20 decode profile contract

- Cluster/node: `prod-maas-h200-jp` / `gpu-h200-36`, gated on zero Kubernetes GPU requests and zero host-visible GPU processes before reservation.
- Target model: `/home/models/zai-org/GLM-5.2-FP8`; target prefixes are tokenized from Liaoze's six-hour GLM-5.2 request corpus without retaining or publishing raw message text.
- Runtime image: `image.hpc-ai.com/platform/dynamo-sglang-runtime@sha256:cd6c3e975a0d3ed7db05a902b551ea4028961a89168171dfc28686624ffc56cc`, matching the live Europe EAGLE deployment.
- Topology: `TP=8`, `DP=1`, `EP=1`, `PP=1` on one eight-H200 node.
- Speculation: EAGLE, five proposal steps, top-k one, six draft tokens, speculative attention mode `decode`.
- Serving mode: standalone real prefill and decode. No disaggregation mode, fake transfer backend, bootstrap host, or bootstrap room is permitted.
- Workload: exactly twenty sequence-distinct 4,096-token real prefixes. Raw customer text must not enter the Japan artifact pack or public report; retain only token IDs, corpus record IDs, timestamps, and token-sequence SHA-256 hashes.
- Warm-up: populate target and draft-side state with unprofiled real requests and verify `/server_info` reports a nontrivial speculative acceptance length.
- Measurement: use an exact local batch of twenty and enough output tokens to observe multiple steady target-verification rounds. Select the final output length after the pilot, then record the value and acceptance statistics here.
- Capture: Nsight Systems CUDA/NVTX/OSRT with CUDA graph-node tracing and CUDA-profiler API range control. Start only after warm-up; stop only after the measured client has consumed and persisted every response.
- Evidence: preserve request outcomes, token counts, acceptance metrics, server logs, image/model fingerprints, `.nsys-rep`, SQLite, compact event exports, and one-rank ownership reconciliation.
- Cleanup: delete every temporary pod after publication and prove that `gpu-h200-36` again has zero Kubernetes GPU requests and zero host-visible GPU processes.
