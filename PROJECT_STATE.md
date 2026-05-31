# ESData project state

Current state source: `docs/master-execution-roadmap.md`.

Operationally, the project is closed as a useful v1 and is now in maintenance-only mode. The honest claim is regulatory consultation with traceability and fail-closed behavior, not automatic fiscal truth.

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
