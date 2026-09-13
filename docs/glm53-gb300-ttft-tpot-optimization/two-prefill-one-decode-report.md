# First 2P1D deployment and doubled-load trial

Current status: the first doubled-load trial was deliberately stopped for growing Prefill backlog. All 4,705 admitted requests completed successfully; 8,764 scheduled requests were never admitted. The deployment is drained, sources and container identities are unchanged. The 12K Prefill candidate is prepared but not applied; shared-cache eviction behavior is being audited first.

Prefill uses four GPUs each on 132 and 151 (PP4/TP1). One Decode replica spans 130 and 192, four GPUs per node, with TP8/DP8/EP8 and 768 total running-request slots. Both Prefill workers use the retained six optimization edits plus request-producer CUDA-event ordering. Decode and frontend retain frozen sources/images. Full values, manifests, overlays, hashes, resource budgets and launch scripts are under preparation/ and rollout/.

All eight pods became Ready at 13:34:59 Singapore. Actual source hashes, images, DP ranks 0–7, local rank partitions, capacities and exact frontend registration were verified. Each Prefill has 9,252,096 logical GPU-cache tokens and 13,878,208 host-cache tokens; Decode has 3,135,616 logical tokens per DP rank. Do not sum Prefill pipeline partitions. Two 650 GiB shared-Store clients on 130 and 192 provide 1,300 GiB raw storage; live fragmentation and publication delays still require sustained-load measurement.

The private frontend registers exactly two Prefill generation instances and one Decode generation instance. The follower has distinct auxiliary indexer endpoints, not a second Decode generation replica. Runtime bindings and health discovery are saved in evidence/.

All 24 predeclared 18K-token retrieval requests passed: eight cold/shared/cold trios, one per Decode DP rank, alternating the Prefill direction. Exact final identifiers, DONE, input counts and cache counts matched. Each cross-Prefill request reused 18,048 tokens; storage-hit counters independently increased by that amount on all four consumer Prefill ranks. Per-rank Decode token counters and Prefill request counters verified routing. Both Prefill replicas actually replayed all four 8K graphs and activated optimized map handling. All 115 engine/frontend queue gauges were zero in two consecutive samples. These are bounded correctness observations, not general accuracy or load-performance claims.

Preserved incidents:

- Store192 initially exhausted master-connection retries while Master130's uncached image was pulling. Kubernetes restarted that Store client once; it then allocated both 325 GiB segments and became healthy. No OOM or inference was involved. The current container/restart baseline is bound and monitored; no healthy restart was forced to erase the count.
- The first cache reset stopped before any RPC because the unused frontend had not created its model gauges yet. A first smoke initialized them.
- That smoke used only eight output tokens and ended normally at the length limit during reasoning, with no final answer. HTTP200/DONE does not make this a successful answer. All raw SSE is retained under first-smoke/. The supplied enable_thinking=false flag did not prevent reasoning in this runtime. The established 256-token correctness fixtures passed; the stress workload remains capped at 20 for comparability. Reported nonempty generated output can include reasoning and is not proof of a complete task answer.

The new real-request capacity-aware dataset contains 400 warmup requests and 13,469 measured requests. Measured input is 600,193,610 tokens, modeled uncached input 59,992,906, over 600 seconds. Every selected payload is distinct and prepared token sequences match the original verified source. Finite-capacity routing/publication sensitivity audits are under ../dataset/candidate04-bounded-uncached-debt/. Actual uncached TPM and storage-hit behavior remain measurements to collect, not established by the plan.

Replay configurations, exact launch/stop controls, generator attestation and collectors are under replay/. The measured workload must follow cache reset, 400-request warmup and full drain. Require all 13,469 identities, zero client errors, every Alex trailing-20s TTFT p50 below 4 seconds, and explicit TPOT-tail analysis. Do not infer the complete OTPS percentile contract from the incomplete three speed pairs.

Prior 1P1D releases, values, full logs and manifests are retained in prior-lanes/. Their in-memory caches were necessarily lost on teardown; compiled caches and source snapshots remain. ATT28 on 151/192 remains the best completed 1P1D trial: all 602 TTFT p50 windows below4s, worst3.064s; TPOT tail remains open.

## ATT29 partial negative result

Alex: http://43.156.43.133:31019/replay/runs/20260913_055201/report?view=overview&columns=overview

The 400-request warmup completed with zero errors. Its TTFT p50 was20.019s andp99 27.279s; TPOTp99 47.946ms. Warmup consumed22,317,649 input tokens,6,667,072 cached and15,650,577 uncached; this cold seeding phase is not a latency pass. It drained before measurement.

The measured trial started at13:52:13.511 Singapore. At13:55:56, admissions were stopped because Prefill backlog and client latency kept increasing. All4,705 admitted requests succeeded, with HTTP200,DONE and nonempty generated output. The last body was sent at222.899s; the last completion was264.508s. There were no bootstrap rejections, new pod restarts or collector fatal triggers. All115queue gauges were idle twice; final direct source hashes, including the cache adapter, match the intended files. Every admitted identity is exactly in the first4,705 entries of the fixed schedule. The8,764 never-admitted requests remain explicitly counted, not hidden as successes.

Across admitted requests, TTFTp50/p99 was10.656/46.960s; TPOTp99 was79.386ms. Independently reconstructed all264 Alex window points. Worst trailing20sTTFTp50 was51.830s during drain;198points exceeded4s. Worst20sTPOTp99 was105.482ms;91requests exceeded40ms and44exceeded80ms. This is a failed partial result, not a complete ten-minute comparison.

Input was223,025,574 tokens and cached input196,695,168, giving26,330,406 uncached tokens and88.1940%hit. Over the observed admission span this is approximately60.034M input/7.088M uncachedTPM. The first minute matched the intended load:59,998,156input/6,003,020uncached,89.9947%hit. The next minute had6,449,462uncached and89.2644%hit; the third7,890,858uncached and86.8701%hit. The partial fourth minute hit86.0291%. There are408requests with less cache than the finite plan and a net4,042,112token cache deficit.

Shared Store allocation rose from837,775,471,104 to1,204,360,873,728bytes. During the run it performed15evictions, deleting2,137,435physical object keys and943,453,596,672bytes. Some large cache deficits occurred10–53seconds after a matching parent completed; another child arrived before a badly delayed parent completed. Queue feedback alone therefore does not explain every cache miss. The offline model's prefix-preserving leaf eviction must not be equated with the live Store's physical-object eviction without further proof.

Early stage counters showed frontend preprocessing around6ms, Prefill bootstrap and final handoff around0.64s each, and rising Prefill queue time. The dataset also has more requests per input token than the original1P1Ddataset:13,469 rather than twice5,921requests. Changes in request mix, L3traffic, eviction and queue feedback all need separation. Generator body-sendp99 was68.75ms, max167.68ms, connectorqueue0; these are much smaller than the observed many-second serving delays.

Evidence: replay/partial-analysis.json; replay/evidence/cache-deficit-parent-timings.json; replay/evidence/DRAINED.json; all six metrics streams, eight pod logs and four-node samples; raw timing export under the follow-up evidence/20260913_055201/. The prepared follow-up changes only Prefill chunk and max-prefill8192→12288 and adds a12288graph bucket. It remains unapplied while the cache retention assumptions are checked.
