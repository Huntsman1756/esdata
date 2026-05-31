# ESData final product coverage matrix

Status: `FUNCTIONAL_CLOSEOUT_BACKUP_DEFERRED`

Last verified: 2026-05-31 on VPS commit `1873445`.

This document is the final user-facing coverage matrix for the current ESData product. It describes what can be used now, what must remain partial, and what must not be claimed.

It does not replace `docs/master-execution-roadmap.md` as the active execution source.

## Product Claim

ESData is usable as a transversal regulatory API/MCP for evidence-backed consultation, audit trails, and human review acceleration.

ESData is not an automatic fiscal, legal, regulatory, sanctions, or compliance decision engine.

## Acceptance Evidence

The final product acceptance gate passed on the VPS:

- `/health`: OK
- `/status`: OK
- workers: `41`
- stale workers: `0`
- worker errors: `0`
- `systemctl --failed`: `0 loaded units listed`
- `scripts/maintenance/final_product_acceptance_gate.py`: `ok=true`, `13/13` canonical checks OK

Backup/offsite restore is intentionally deferred. That means functional product closeout is accepted, but disaster-recovery closeout is not claimed.

## Coverage States

- `usable`: scoped queries can return official source/evidence and explicit evidence status.
- `partial`: real data and API/MCP surface exist, but coverage is incomplete.
- `partial_traceable`: partial corpus with traceable sources, suitable for review workflows.
- `very_limited`: small corpus or narrow workflow only.
- `workflow_empty`: flow exists but returns explicit fail-closed output.
- `not_exposed`: data or worker may exist, but no accepted user surface is exposed.

## Final Matrix

| Domain | State | Use Now | Do Not Claim | Canonical Gate Evidence |
| --- | --- | --- | --- | --- |
| Infra health | `usable` | Check API and DB availability. | That all domain data is complete. | `/health` |
| Worker status | `usable` | Check worker freshness/errors. | That every external source is exhaustive. | `/status` |
| Domain availability | `usable` | Detect empty/partial domains before answering. | That empty means legally nonexistent. | `/v1/domain-availability` |
| BOE legislation | `usable` | Retrieve scoped legislation and article evidence with BOE references. | Full Spanish legal coverage. | `/v1/legislacion/LIVA` |
| AEAT models | `partial` | Inspect model metadata, sources, casillas and operational summaries. | Automatic filing obligations or campaign assertions without direct official evidence. | `/v1/modelos/124/resumen-operativo` |
| DGT/TEAC doctrine | `partial_traceable` | Search and review doctrinal lines with explicit completeness/safety fields. | Complete doctrine or binding answer without `safe_to_answer=true`. | `/v1/doctrina/lineas/coverage` |
| CNMV | `partial` | Review loaded CNMV families and distinguish loaded vs unavailable families. | Complete CNMV universe, registers, Q&A, or all supervisory material. | `/v1/cnmv/coverage` |
| EUR-Lex / ESMA markets | `usable` | Query loaded market acts, articles and ESMA-related regulatory artifacts. | Complete EU regulatory corpus. | `/v1/eurlex/market/acts` |
| MiCA / CASP | `usable` | Query loaded CASP register and MiCA-related obligations where present. | Full crypto-asset regulatory coverage. | `/v1/mica/casp` |
| Screening / sanctions | `usable` | Query loaded official screening entries by list/source. | That no match means no sanctions risk unless the source contract explicitly supports that conclusion. | `/v1/screening/entries?codigo=EU_SANCTIONS&limit=1` |
| AEPD | `partial` | Review loaded AEPD official documents with partial coverage metadata. | Full data-protection compliance answer. | `/v1/aepd` |
| SEPBLAC | `partial` | Review loaded SEPBLAC documents with partial coverage metadata. | Full PBC/FT decisioning by subject/profile. | `/v1/sepblac` |
| BDE | `partial` | Review loaded Banco de Espana documents with partial coverage metadata. | Complete banking-supervision coverage. | `/v1/bde` |
| BORME | `partial` | Use only where specific endpoints/data are exposed and traceable. | Complete corporate registry coverage. | Covered by broader corpus inventory, not final gate smoke. |
| BOE diario | `partial` | Review loaded non-consolidated BOE daily documents. | Consolidated law status or complete BOE daily universe. | Covered by broader corpus inventory, not final gate smoke. |
| BDNS | `very_limited` | Narrow subsidy-document checks only. | Broad subsidy coverage. | Covered by broader corpus inventory, not final gate smoke. |
| CENDOJ | `very_limited` | Narrow loaded-document checks only. | Broad jurisprudence coverage. | Covered by broader corpus inventory, not final gate smoke. |

## Response Interpretation

Treat these fields as blockers for automatic answers:

- `safe_to_answer=false`
- `verified=false`
- `review_required=true`
- `completeness=partial`
- `row_completeness=partial`
- `coverage_status=partial_loaded`
- `availability_status=configured_but_unavailable`
- missing `source_url`, `url_fuente`, `boe_id`, `eli_uri`, or equivalent source reference

When any blocker is present, the correct behavior is to show the limitation and keep the answer in review mode.

## Final Operating Rule

Use ESData to find, cite, compare, audit, and accelerate review.

Do not use ESData to decide automatically that an obligation exists, does not exist, is fulfilled, or is not applicable unless the specific endpoint returns explicit evidence and safety status for that exact claim.
