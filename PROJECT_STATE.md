# ESData project state

Current state source: `docs/master-execution-roadmap.md`.

Operationally, the project is closed as a useful v1 and is now in maintenance-only mode. The honest claim is regulatory consultation with traceability and fail-closed behavior, not automatic fiscal truth.

Functional closeout release tag: `v1.15.0`.

Current operational review tag: `v1.15.4`. This preserves `v1.15.3` administrative closeout and records the live sources/jobs review, CNMV ingestion hardening, and green MCP validation/deep-audit evidence.

Latest runtime evidence:

- BDNS structured ingestion is deployed and queryable with official-exact `convocatoria_bdns` and `concesion_bdns` rows.
- BORME official-summary ingestion is deployed and queryable with `official_best_effort` extraction metadata.
- `/health` is OK on the VPS.
- `systemctl --failed` is clean on the VPS.
- `esdata-mcp-validation.service` passes with `ok=true`.
- `esdata-mcp-deep-audit.service` passes with `ok=true`.
- Weak DORA/MiCA duplicate rows, CNMV missing `sujeto_obligado`, and legacy `BDNS-CONCESION-unknown` artifacts are at `0`.
- `/status` reports `41` workers, `0` stale, `0` errors, and `worker-cnmv` as partial only because 20 externally hosted CNMV documents fail fetch; this is not a semantic gate failure after the subject-tag remediation.

Explicitly deferred:

- Offsite backup configuration and restore drill remain outside this administrative closeout by operator decision. They must be handled as a separate operations block before claiming full disaster-recovery readiness.

Scheduled maintenance gates:

- `esdata-mcp-validation.timer`: hourly read-only smoke via `mcp_validation_suite.py`.
- `esdata-mcp-deep-audit.timer`: daily read-only deep audit via `mcp_deep_contract_audit.py`.

Manual release gates:

- `scripts/maintenance/source_assurance_gate.py`: static source-claim gate. No domain is certified as exhaustive; broad source coverage claims fail the gate.
- `scripts/maintenance/response_verifiability_gate.py`: answer-source gate. Any actionable consulta/MCP answer must expose searchable source locators in the response itself (`source_url`, `source_hash`, `cited_chunks`, `claim_citations`, or `result_metadata.source_verification`) or remain `safe_to_answer=false`.

Allowed maintenance work:

- operational failures
- security fixes
- gate regressions
- real alerts
- dependency changes required to keep the service healthy
- state documentation

Not allowed without explicit v2 opening:

- new features
- new source families
- claim expansion
- new curation sprints
- AEAT campaign promotion

Hermes AEAT is expected to keep models `124`, `126`, and `128` in human review when evidence is insufficient:

- `decision=CONFLICT`
- `campana_safe_to_assert=false`
- `human_review_required=true`
- no promotion to operational fiscal data

Future exit from that state requires direct, verifiable official evidence for the campaign. If evidence cannot be verified, the state remains fail-closed.
