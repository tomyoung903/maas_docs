# Native progress dependency recovered after ATT51 startup failure

The revised CPU model reproduces a candidate-only progress failure when the first batch arrives after12idle/control iterations and the first tensor send cannot return until its receiver participates. The baseline passes that case. Both variants pass when their first batch is immediate, and both pass with the cold-send host wait disabled. The initial tests started batches immediately, so they initialized the modeled tensor path before the reordered bootstrap receive became relevant.

Actual source loops, control frames and metadata methods execute, but tensor transport remains a model. The coldsend host gate is an inference from two native candidateincarnations observed inside the first torch.distributed.isend/PP1earlyreceive wait pattern. These cases narrow the cause; they do not prove a native priming remedy or general KVcorrectness. The second native incarnation was an incorrectly retained candidate child under Grove during rollback, not a failed baseline control.

Tool44866 completed with exit0. All six cases and originalsource hashes are in RESULT.json and VERIFIED.json. No GPUs, servingconfiguration, requestbodies or outputpolicies were changed by this CPUtest. Transport priming remains a separate unimplemented lead, requiring a bounded native test and then full model and performance qualification.

## Subsequent native fixture — 14 September, 03:01 Singapore

`native-validation-01/REPORT.md` records a separate four-rank, tiny-tensor test on idle Prefill132. The first individual NCCL sends waited on the host for delayed receivers; after matching individual peer priming, the calls returned early. All values matched and helpers were confirmed absent afterward. This supports the initialization mechanism, not a full model remedy or a TTFT gain. Sender-local completion is distinct from peer receipt.

A new prepared source revision, `../../candidates/early-bootstrap-primed/`, adds explicit startup priming before the earlier bootstrap-adoption loop. Its source is73aaee2728ce0a1ef571d62a7e52c22e74f6142dabbb9377db225f20bddf0ac6. Three exact-helper cases and eleven guard cases passed. It remains undeployed and requires full model startup, correctness and performance qualification after ATT53. The rejected ATT51 source and its closed archive remain unchanged.
