# 80K rerun code and control ledger

This rerun introduces **zero new serving optimization patches**. It retains the historical ATT56/ATT57 SGLang overlays and native frontend. Current-dev draft ports were not substituted. Their separate delivery record remains `/mnt/HPC/tom/pd-latency-followup-20260913/pr-delivery-20260914/DELIVERY.md`; summary issue: https://git.luchentech.com/maas/sglang/-/issues/5.

The new code is for dataset selection, controlled reproduction and evidence analysis. All paths below are relative to this investigation root.

| Purpose | Files / evidence |
|---|---|
| Original-request 80K selection | `select_80k.py`, `finite_plan_80k_chain_lookahead.py`, selected candidate JSON, `SEARCH-LEDGER.json` |
| Independent original-token prefix oracle | `audit_token_prefix_oracle.py`, both candidate token-prefix-oracle receipts |
| Finite-cache and two-Prefill routing sensitivity | `audit_2p_cache.py`, `audit_2p_tiers.py`, candidate audits |
| Immutable pack transfer, registration and CPU Prepare | `publish_1p1d.py`, `prepare_1p1d.py`, `verify_1p1d.py`, 2P equivalents, `recover_publish_2p1d.py` |
| Scoped serving restore and 2P-to-1P transition | `serving/`, `transition_to_1p.py`, bound pod/container identity receipts |
| Original-output qualification and run controls | `prepare_1p_controls.py`, `init_1p_observers.py`, `continue_1p_after_warmup.py`, `run-1p1d-80k/replay/` |
| Executed configuration verification | `attest_run_config.py`, per-arm `replay/evidence/*-executed-config.json` |
| Immutable raw scalar export and independent chart reconstruction | `export_run.py`, `analyze_run.py`, `analysis-validation/VERIFIED.json` |
| Actual rolling input/uncached traffic and exact violation duration | `audit_live_rolling.py`, `audit_live_duration.py` |
| Missing-generation median sensitivity | `bound_missing_generation_medians.py` |
| Passive Prefill/L3 trajectory and collector closure | `summarize_prefill_trajectory.py`, `close_collectors.py` |
| Public aggregate record and desktop validation | `docs/build_80k_report.py`, `docs/validate_80k.mjs` |

The sole historical placement difference is the 16GiB Mooncake metadata-master reservation moving from node 130 to 192 for the RAM preflight. This is documented in `serving/METADATA-MASTER-PLACEMENT.json`. It does not change worker pool sizes or model-worker placement. The 1P transition changes only Prefill replicas from two to one and releases node 151.

## Reproduction fixes and retained incidents

- The 2P pack-transfer connection returned a websocket EOF after all files arrived. Every file and payload frame was independently verified before its manifest was accepted. Error and recovery receipts remain preserved.
- The first 1P runtime watcher lacked its existing `quiet_store_log_renewal.py` helper. This failed before traffic. The exact historical helper was copied and the preparation script corrected; the watcher then started successfully. The helper renews only owned Store log streams.
- Before the 1P measured launch, the copied observer's old 5,921-request expectation was corrected to 3,760. The warmup count remains 100. The prior file and correction receipt remain under `run-1p1d-80k/replay/evidence/`. No traffic or serving behavior changed.
- Immediately after 1P measured launch, Alex's initial run metadata had not yet acquired its dataset fields. The post-launch attester failed on the absent field while the accepted replay continued normally. A dedicated observer was promptly started; a subsequent read verified the correct dataset/profile and `request_max_tokens=null`. The attester now waits only for absent dataset metadata, with a bounded timeout; populated mismatches still fail immediately. No request was relaunched.
- During warmup, the raw event file had 96 persisted rows while the live snapshot showed 99 completions. This was a partial-file buffering observation. The final warmup accounting is 100/100 meaningful successes; partial-file absence was not treated as a failed response.

Existing generator code, shared SGLang checkout changes, and unrelated deployments were not modified.
