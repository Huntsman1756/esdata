# ESData release closeout gate

This file defines the pass/fail contract for closing the current useful v1 release. If a criterion cannot be verified, the gate fails.

## Product claim

ESData is useful for evidence-backed regulatory consultation, audit trails, and human review acceleration. It is fail-closed and does not act as an automatic fiscal decision engine.

## Pass criteria

- `systemctl --failed` returns `0 loaded units listed`.
- The latest `hermes-esdata-curator.service` run has `Result=success` and `ExecMainStatus=0`.
- The latest Hermes AEAT batch has `OK` for the daily-cap models and `DAILY_CAP_REACHED` for the remaining queued models; no `ERROR_*` rows are allowed.
- `legal-sources` rows include explicit statuses or reasons. Bare `SKIPPED` is not acceptable.
- The latest ops report has no known permission warnings, including `infra/deploy/secrets/alertmanager`.
- `mcp_validation_suite` passes.
- `mcp_deep_contract_audit.py` passes when run from the `ops` container.
- `/health` passes. `/status` must either pass or be explicitly documented as unavailable with cause.
- AEAT models `124`, `126`, and `128` remain documented as `CONFLICT`, `campana_safe_to_assert=false`, and `human_review_required=true` unless new direct official evidence changes the state.
- No campaign data is promoted from LLM inference. `resolved_strong` requires direct, verifiable official evidence.

## Failure criteria

- Hermes reports systemd success while internal logs contain execution errors.
- `legal-sources` contains ambiguous `SKIPPED` rows.
- Known permission warnings are mixed into the final ops report.
- Any model row is `ERROR_*` without a documented cause.
- Documentation presents target-state behavior as implemented.
- `mcp_deep_contract_audit.py` reports missing MCP/OpenAPI operations, DB registry failures, FK orphan failures, or semantic contract failures.
