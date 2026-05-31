# ESData project state

Current state source: `docs/master-execution-roadmap.md`.

Operationally, the project is closed as a useful v1 and is now in maintenance-only mode. The honest claim is regulatory consultation with traceability and fail-closed behavior, not automatic fiscal truth.

Functional closeout release tag: `v1.15.0`.

Current hardened closeout tag: `v1.15.1` for source assurance. This adds a deterministic gate that prevents broad source/exhaustiveness claims from entering active docs, OpenAPI, MCP/API descriptions, or final coverage artifacts.

Scheduled maintenance gates:

- `esdata-mcp-validation.timer`: hourly read-only smoke via `mcp_validation_suite.py`.
- `esdata-mcp-deep-audit.timer`: daily read-only deep audit via `mcp_deep_contract_audit.py`.

Manual release gates:

- `scripts/maintenance/source_assurance_gate.py`: static source-claim gate. No domain is certified as exhaustive; broad source coverage claims fail the gate.

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
