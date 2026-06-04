# ESData final product coverage matrix

Status: `FUNCTIONAL_CLOSEOUT_BACKUP_DEFERRED`

Last verified: 2026-05-31 on the VPS during `SOURCE-CLOSEOUT-AUDIT-01`.

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
- `scripts/maintenance/final_product_acceptance_gate.py`: `ok=true`, `30/30` canonical checks OK
- `mcp_validation_suite.py --read-only`: `ok=true`, `tool_count=91`
- `mcp_deep_contract_audit.py`: `ok=true`, with GPT Actions OpenAPI regenerated from `HTTP_MCP_OPERATIONS`

Backup/offsite restore is intentionally deferred. That means functional product closeout is accepted, but disaster-recovery closeout is not claimed.

## Coverage States

- `usable`: scoped queries can return official source/evidence and explicit evidence status.
- `partial`: real data and API/MCP surface exist, but coverage is incomplete.
- `partial_traceable`: partial corpus with traceable sources, suitable for review workflows.
- `very_limited`: small corpus or narrow workflow only.
- `workflow_empty`: flow exists but returns explicit fail-closed output.
- `not_exposed`: data or worker may exist, but no accepted user surface is exposed.
- `internal_support`: operational/governance surface, not a product source claim.
- `out_of_scope`: mounted or historical code exists, but it is not part of the accepted product claim.

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
| EUR-Lex market acts | `usable` | Query loaded market acts/articles where ESData exposes article/source metadata. | Complete EU regulatory corpus. | `/v1/eurlex/market/acts` |
| ESMA MiFIR schemas/reporting | `partial` | Review loaded schema fields, reporting documents and validation rules. | Complete ESMA reporting coverage, FIRDS/FITRS/full datasets. | Broader source audit; not all ESMA subfamilies are final-gate product claims. |
| ESMA FIRDS/FITRS | `very_limited` | FIRDS file metadata only; instrument-level ISIN payloads intentionally unavailable. | Full or sampled instruments universe. | Broader source audit only. |
| MiCA CASP register | `usable` | Query loaded CASP register entries. | Full MiCA or crypto-asset regulatory coverage. | `/v1/mica/casp` |
| MiCA issuer / ART / EMT workflows | `partial` | Use only where obligations are explicitly sourced. | Complete issuer-token applicability. | Broader inventory; not a CASP-register claim. |
| Screening OFAC SDN | `usable` | Query loaded OFAC entries by official list. | EU/UN/SEPBLAC sanctions or PEP coverage. | `/v1/screening/entries?codigo=OFAC_SDN&limit=1` |
| Screening EU sanctions | `usable` | Query loaded EU restrictive-measures entries. | That no match means no sanctions risk across all sources. | `/v1/screening/entries?codigo=EU_SANCTIONS&limit=1` |
| Screening UN / SEPBLAC / PEP | `not_exposed` | Do not use as product coverage today. | Any screening conclusion for unloaded sources. | Explicitly outside accepted loaded screening sources. |
| AEPD | `partial` | Review loaded AEPD official documents with partial coverage metadata. | Full data-protection compliance answer. | `/v1/aepd` |
| SEPBLAC | `partial` | Review loaded SEPBLAC documents with partial coverage metadata. | Full PBC/FT decisioning by subject/profile. | `/v1/sepblac` |
| BDE | `partial` | Review loaded Banco de Espana documents with partial coverage metadata. | Complete banking-supervision coverage. | `/v1/bde` |
| BORME | `partial` | Use loaded BORME acts with official BOE URL, related-company links and heuristic appointment metadata. | Complete corporate registry coverage or certified company/officer state. | `/v1/borme` |
| BOE diario | `partial` | Review loaded non-consolidated BOE daily documents. | Consolidated law status or complete BOE daily universe. | `/v1/boe-diario` |
| BDNS | `partial_loaded` | Use structured official rows when loaded (`convocatorias`, `concesiones` and related endpoint families) with fail-closed response contract. | Broad or exhaustive subsidy coverage. | `/v1/bdns` |
| CENDOJ | `very_limited` | Narrow loaded-document checks only. | Broad jurisprudence coverage. | `/v1/cendoj` |
| CDI / DTA convenios | `partial` | Explore loaded double-tax conventions and treaty metadata as inventory. | Definitive withholding result by country/article/income type without dedicated evidence. | `/v1/internacional/convenios`; inventory-only until source provenance fields are added. |
| CRS / DAC2 / FATCA / GIIN | `partial` | Review loaded IRS/GIIN/FATCA/CRS references and model metadata as inventory. | Complete CRS/DAC2 or FATCA procedure coverage. | `/v1/irs-fiscal/giin`; inventory-only until source provenance fields are added. |
| PSD2 / SEPA | `partial` | Review loaded PSD2/SEPA reference records as inventory. | Complete payment-regulatory coverage. | `/v1/psd2/sepa-rules`; inventory-only until source provenance fields are added. |
| PGC / XBRL / ESEF | `partial` | Use loaded PGC/XBRL surfaces for narrow inventory checks. | Complete accounting/reporting engine. | Broader inventory; source assurance not certified for final answers. |
| DORA / SFDR / CSRD / AIFMD / UCITS / CRD / EMIR / MiFID / MAR / PRIIPs / PBC / fraud | `out_of_scope` | Treat mounted endpoints as development or narrow operational surfaces unless a specific contract says otherwise. | Final accepted source coverage. | Not in accepted final product gate. |
| Source manifest / freshness | `internal_support` | Inspect freshness for Wave 1 sources. | Complete source inventory of all workers. | `/v1/sources/manifest` covers only Wave 1 manifest rows. |
| Regulatory watch / source_revision | `internal_support` | Operational change detection and telemetry. | User-facing legal-change corpus unless exposed by a specific endpoint. | No direct final product source surface. |
| AI governance / human review / query audit / observability | `internal_support` | Audit and governance operations. | External legal/regulatory source coverage. | Operational support only. |

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
