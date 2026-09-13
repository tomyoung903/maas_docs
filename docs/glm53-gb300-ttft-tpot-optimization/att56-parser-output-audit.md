# Incomplete bare GLM tool-call output suppression

At05:43Singapore, both retained trace correlation and a CPU reproduction identify an existing parser path relevant to the missing-output gate.

ATT55: all17missing-generation successes have a matching orphan tool-call warning. ATT56:22of23match; the remaining response finished withstop and4completion tokens. Every matching warning snippet begins with`<arg_key>` and lacks`</tool_call>`; none reaches the logger snippet cap. The logger starts at the orphan marker, so the complete preceding function name and backend token stream are unavailable.

The exact compiled parser library passes10synthetic checks: an incomplete bare call returns zero calls and empty text with EOF recovery both off and on. A complete bare call recovers one structured call. A framed incomplete call returns raw text only with EOF recovery on. Ordinary prose survives both settings. This asymmetry predates the UTF8 offset fix; the new fix only changes the argument slicing boundary.

This establishes a suppression path, not the upstream origin of malformed/truncated generation. The20token cap can leave calls incomplete, but the missing opening marker is not explained. It is not evidence of a rejection-sampler defect. Do not manufacture a visible token, impute missing TTFT, or count this gate as passed. Preserve all23missing responses in ATT56 acceptance accounting. No serving setting was changed for the audit or reproduction.

Evidence: sibling attempt55/56-missing-generation-traces/ORPHAN-CORRELATION.json; private exact matches beside those files; probe.rs, compile/execute intents and exits, VERIFIED.json here. The12unloaded chosen-token probes all generated visible text but returned no requested logprobs, providing no backend token explanation. The earlier unsupported top-logprob probes caused8streamed errors and a300second Prefill timeout cleanup delay; all were drained before ATT57.
