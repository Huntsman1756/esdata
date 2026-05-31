# ESData release closeout gate

This file defines the pass/fail contract for closing the current useful v1 release. If a criterion cannot be verified, the gate fails.

## Product claim

ESData is useful for evidence-backed regulatory consultation, audit trails, and human review acceleration. It is fail-closed and does not act as an automatic fiscal decision engine.

## Current closeout snapshot

Administrative closeout tag: `v1.15.3`.

This closeout includes the BDNS/BORME structured-ingestion rollout and the post-deploy validation fixes needed to keep the VPS gates green:

- BDNS official structured rows are ingested as bounded, traceable subsidy data, with fail-closed API semantics.
- BORME official BOE summary/PDF rows are ingested with explicit best-effort extraction metadata.
- MCP validation, deep audit scheduling, source-assurance gates, answer-verifiability gates, and operational health checks remain part of the release contract.

Offsite backup configuration and restore drill are explicitly not part of this snapshot. They remain a separate operations block and must not be represented as completed disaster-recovery readiness.

## Pass criteria

- `systemctl --failed` returns `0 loaded units listed`.
- The latest `hermes-esdata-curator.service` run has `Result=success` and `ExecMainStatus=0`.
- The latest Hermes AEAT batch has `OK` for the daily-cap models and `DAILY_CAP_REACHED` for the remaining queued models; no `ERROR_*` rows are allowed.
- `legal-sources` rows include explicit statuses or reasons. Bare `SKIPPED` is not acceptable.
- The latest ops report has no known permission warnings, including `infra/deploy/secrets/alertmanager`.
- `mcp_validation_suite` passes.
- `mcp_deep_contract_audit.py` passes when run from the `ops` container.
- `source_assurance_gate.py` passes. No active product doc, OpenAPI file, MCP/API description, or final coverage artifact may claim exhaustive coverage of a regulatory domain.
- `response_verifiability_gate.py` passes. Actionable MCP/API answers must expose verifiable `source_url` or `source_hash` in the response itself, or return `safe_to_answer=false`.
- `/health` passes. `/status` must either pass or be explicitly documented as unavailable with cause.
- AEAT models `124`, `126`, and `128` remain documented as `CONFLICT`, `campana_safe_to_assert=false`, and `human_review_required=true` unless new direct official evidence changes the state.
- No campaign data is promoted from LLM inference. `resolved_strong` requires direct, verifiable official evidence.

## Failure criteria

- Hermes reports systemd success while internal logs contain execution errors.
- `legal-sources` contains ambiguous `SKIPPED` rows.
- Known permission warnings are mixed into the final ops report.
- Any model row is `ERROR_*` without a documented cause.
- Documentation presents target-state behavior as implemented.
- Documentation or API metadata claims complete/all/exhaustive coverage for Hacienda, BOE, CNMV, Banco de Espana, EUR-Lex, ESMA, sanctions, or any other source family unless a separate deterministic source certification exists.
- `/v1/consulta` or MCP metadata can return `safe_to_answer=true` without sources searchable in `result_metadata.source_verification`, `cited_chunks`, or `claim_citations`.
- `mcp_deep_contract_audit.py` reports missing MCP/OpenAPI operations, DB registry failures, FK orphan failures, or semantic contract failures.

## Deferred operations

- `BACKUP-OFFSITE-RESTORE-01`: configure a real offsite backup target, run the backup from production, restore into an isolated environment, verify schema/data accessibility, and record evidence in the roadmap before claiming disaster-recovery readiness.
