# ESData final product acceptance plan

Status: `DEFINED_NOT_STARTED`

Purpose: close ESData as a transversal regulatory MCP product, not as an incremental AEAT curation sprint.

This plan does not open new product work by itself. It defines the acceptance gate for declaring ESData finished as a useful, honest, operable product.

## 1. Objective

Demonstrate that ESData is a transversal regulatory MCP for evidence-backed consultation, audit trails, and human review acceleration. It is fail-closed and does not replace expert fiscal, legal, or regulatory decision-making.

Success criterion:

> A user can query the main regulatory domains through API/MCP surfaces and receive official evidence, clear limits, and fail-closed behavior.

Non-success criterion:

> Resolving more individual AEAT models does not, by itself, finish the product.

## 2. Current Live Inventory Basis

The acceptance gate must use live evidence from the VPS, not roadmap memory.

Minimum inventory inputs:

- `systemctl --failed`
- authenticated `/status`
- `/health`
- `mcp_validation_suite`
- OpenAPI path list
- `HTTP_MCP_OPERATIONS` from `apps/api/mcp_catalog.py`
- `sync_log` latest row per worker
- row counts for key tables and shared corpus tables
- representative query per accepted domain

Observed snapshot on 2026-05-31:

- `/status`: `41` workers, `0` stale, `0` error
- OpenAPI: `413` paths
- HTTP MCP: `83` operations
- Core populated data includes AEAT, BOE legislation, DGT/TEAC, CNMV, BORME, BOE diario, AEPD, SEPBLAC, BDE, BDNS, CENDOJ, EUR-Lex/ESMA, CASP, PSD2, screening, and source revisions

## 3. Domain Classification

The final matrix must classify each domain from live evidence only.

Allowed states:

- `usable`: returns official source/evidence and explicit evidence status for scoped queries.
- `partial`: has real data and endpoints, but coverage is incomplete.
- `partial_traceable`: partial corpus with traceable source references, suitable for review.
- `very_limited`: only a small corpus is loaded; useful for narrow checks only.
- `workflow_empty`: flow exists but intentionally returns empty/fail-closed output.
- `not_exposed`: data or worker may exist, but no accepted API/MCP surface is exposed.
- `unknown`: cannot be verified; blocks final acceptance until resolved or downgraded.

Initial live classification to verify in the final gate:

| Domain | Initial state | Evidence note |
| --- | --- | --- |
| AEAT models/catalog | `partial` | Large corpus loaded; campaign assertions remain fail-closed where evidence is insufficient. |
| BOE legislation | `usable` | `articulo` and `version_articulo` populated; API/MCP operations exposed. |
| DGT/TEAC doctrine | `partial_traceable` | Shared `documento_interpretativo` corpus populated with DGT/TEAC. |
| CNMV | `partial` | CNMV corpus and coverage endpoint exist; worker state may be partial without errors. |
| EUR-Lex / ESMA markets | `usable` | EUR-Lex acts/articles and ESMA MiFIR/DLT artifacts populated by block. |
| MiCA / CASP | `usable` | CASP register populated; crypto-asset workflows may still be empty. |
| Screening / sanctions | `usable` | Screening lists and entries populated. |
| BORME | `partial` | Data exists in shared interpretative corpus. |
| BOE diario | `partial` | Data exists in shared interpretative corpus. |
| AEPD | `partial` | Small corpus loaded; no claim of full coverage. |
| SEPBLAC | `partial` | Small corpus loaded; no claim of full coverage. |
| BDE | `partial` | Very small corpus loaded; use only for scoped checks. |
| BDNS | `very_limited` | Minimal corpus; no broad subsidy coverage claim. |
| CENDOJ | `very_limited` | Minimal corpus; no broad jurisprudence coverage claim. |

## 4. Allowed Product Claims

Allowed:

- ESData provides a transversal regulatory API/MCP with official-evidence grounding.
- ESData supports consultation, audit, and human review workflows.
- ESData exposes explicit partial/limited/empty states rather than inventing.
- ESData can answer scoped queries where official evidence is present and traceable.

Not allowed:

- Automatic fiscal/legal decisioning.
- Complete coverage of Hacienda, CNMV, BOE, ESMA, or any broad regulatory universe.
- AEAT campaign promotion without direct official evidence.
- `resolved_strong` from LLM inference, internal persisted state, filenames, version labels, BOE dates, or technical endpoints alone.
- Treating empty results as proof that no obligation/source exists unless the domain contract explicitly supports that conclusion.

## 5. Fail-Closed Response Rules

A response must be treated as fail-closed when:

- official evidence is missing
- source URL or reference is missing
- evidence status is absent
- the domain is partial and no unambiguous match exists
- the domain is `workflow_empty`, `not_exposed`, `very_limited`, or `unknown`
- evidence freshness cannot be verified where freshness is part of the claim

The response may use domain-specific fields such as `safe_to_answer=false`, `evidence_limited`, `verified=false`, `completeness=partial`, `availability_status`, or an equivalent explicit status.

## 6. Final Gate Blockers

The product acceptance gate fails if:

1. `systemctl --failed` is not clean.
2. `/health` fails.
3. authenticated `/status` fails, reports stale workers, or reports worker errors.
4. `mcp_validation_suite` fails.
5. Hermes hides internal errors behind systemd success.
6. Legal-source audit includes ambiguous bare `SKIPPED`.
7. A canonical query returns an affirmative answer without source/evidence.
8. A canonical query returns empty output without fail-closed status.
9. A canonical query lacks evidence status.
10. Documentation presents partial or target-state coverage as complete.
11. Backup/restore status is undocumented in the final closeout.

## 7. Canonical Query Set

The final gate should include 30-50 canonical checks. A smaller smoke can be used while developing the gate, but final acceptance needs broad coverage.

Minimum domain examples:

- AEAT: model detail, official sources, operational summary, fail-closed campaign case.
- BOE legislation: known norm, article list, article detail, version/history where supported.
- DGT/TEAC: doctrine search and detail with traceable reference.
- CNMV: list/search document and coverage endpoint.
- EUR-Lex/ESMA: market act/article, MiFIR schema/fields/rules, DLT infrastructure.
- MiCA/CASP: CASP list/search/detail.
- Screening: screening entries by list code.
- BORME / BOE diario: list and detail for known loaded reference.
- AEPD / SEPBLAC / BDE: list and detail where corpus exists; classify as partial.
- BDNS / CENDOJ: very-limited query that proves honest behavior, not broad coverage.
- Infra: `/health`, authenticated `/status`, `mcp_validation_suite`, latest worker states.

Each canonical check must assert:

- response is HTTP 2xx or an expected explicit fail-closed status
- official source/reference exists when the response is affirmative
- evidence/completeness/safety status exists
- no unsupported broad claim is made

## 8. Smoke Transversal

Create a script or runbook for the final acceptance gate.

Required behavior:

- exits non-zero on any blocker
- records the tested endpoint/tool and input
- records a short reason for every failure
- distinguishes `partial` and `fail-closed` from hard failures
- does not require Hermes generation to pass the product gate

Recommended location:

- script: `scripts/maintenance/final_product_acceptance_gate.py`
- output: JSON summary plus markdown report under a deterministic report path

## 9. Final MCP Manual

The user-facing manual must explain:

- how to connect to HTTP MCP
- how HTTP MCP differs from stdio MCP
- which operations are stable for each domain
- which domains are partial or very limited
- how to interpret `safe_to_answer=false`, `verified=false`, `completeness=partial`, `availability_status`, and `evidence_limited`
- examples that should answer
- examples that should refuse or return fail-closed status

The manual must not require knowledge of repo internals.

## 10. Backup / Restore

Backup offsite is a technical P0 for formal production closure, but it can be tracked separately from the product acceptance plan.

Known current state:

- local/host backup and historical restore drill exist
- offsite backup script and runbook exist
- VPS has `rclone`
- `/etc/esdata/offsite-backup.env` is not present
- `/etc/cron.d/esdata-offsite-backup` is not installed

Formal closeout should document one of:

- offsite backup and restore drill completed, or
- production closure explicitly excludes offsite disaster recovery and records that residual risk

## 11. Activation

This plan does not execute by inertia.

Opening the final product acceptance work requires:

1. Plan merged into `main`.
2. Plan deployed to the VPS.
3. Roadmap updated with a `final-product-acceptance-gate` section including files, acceptance criteria, and verification commands.
4. Explicit commit message: `feat(final): open product acceptance gate`.

## 12. Done Criteria

ESData can be declared finished as a product when:

- every main domain is classified from live evidence
- every accepted domain has at least one passing canonical query
- partial/limited/empty domains are documented honestly
- the transversal smoke passes on the VPS
- the user manual explains actual API/MCP usage and limits
- the v1 fail-closed gate remains clean
- backup/restore risk is either closed or explicitly accepted

