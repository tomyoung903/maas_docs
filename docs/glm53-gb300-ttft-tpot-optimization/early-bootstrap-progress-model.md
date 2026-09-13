# Native progress dependency recovered after ATT51 startup failure

The revised CPU model reproduces a candidate-only progress failure when the first batch arrives after12idle/control iterations and the first tensor send cannot return until its receiver participates. The baseline passes that case. Both variants pass when their first batch is immediate, and both pass with the cold-send host wait disabled. The initial tests started batches immediately, so they initialized the modeled tensor path before the reordered bootstrap receive became relevant.

Actual source loops, control frames and metadata methods execute, but tensor transport remains a model. The coldsend host gate is an inference from two native candidateincarnations observed inside the first torch.distributed.isend/PP1earlyreceive wait pattern. These cases narrow the cause; they do not prove a native priming remedy or general KVcorrectness. The second native incarnation was an incorrectly retained candidate child under Grove during rollback, not a failed baseline control.

Tool44866 completed with exit0. All six cases and originalsource hashes are in RESULT.json and VERIFIED.json. No GPUs, servingconfiguration, requestbodies or outputpolicies were changed by this CPUtest. Transport priming remains a separate unimplemented lead, requiring a bounded native test and then full model and performance qualification.
