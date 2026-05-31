# Source Closeout Audit - 2026-05-31

Status: `COMPLETED_WITH_REMEDIATIONS`

Scope: exhaustive source audit requested before continuing the project. Backup/offsite restore is explicitly out of scope for this block.

## Executive Result

The project is not missing a single obvious production source worker, but the previous closeout was too narrow in three areas:

1. The final coverage matrix accepted a smaller product surface than the REST API actually exposes.
2. The source compliance register only covered AEAT.
3. The final product gate was a 13-check smoke, while the acceptance plan required a broader 30-50 check gate.

This audit remediates those issues by tightening the matrix, expanding source compliance registration, adding explicit BDNS/CENDOJ fail-closed metadata, exposing BDE/BDNS/CENDOJ/SEPBLAC through HTTP MCP, and expanding `final_product_acceptance_gate.py`.

## Live VPS Evidence

Observed on 2026-05-31:

- `systemctl --failed`: `0 loaded units listed`
- `/health`: `status=ok`, `database=ok`
- `/status`: `41` workers, `0` stale, `0` errors
- current deployed commit before remediation: `60e8c51`
- final gate before remediation: `ok=true`, `13/13` checks OK

Key populated tables:

| Table | Rows |
| --- | ---: |
| `aeat_modelo` | 219 |
| `modelo_casilla` | 33374 |
| `modelo_recurso` | 38128 |
| `articulo` | 1970 |
| `version_articulo` | 3512 |
| `documento_interpretativo` | 19764 |
| `source_revision` | 20303 |
| `eurlex_article` | 490 |
| `esma_schema_field` | 168 |
| `esma_validation_rule` | 223 |
| `screening_entries` | 25047 |
| `screening_lists` | 3 |

`documento_interpretativo` by source:

| Source | Rows |
| --- | ---: |
| DGT | 18631 |
| TEAC | 562 |
| BORME | 201 |
| BOE diario | 170 |
| CNMV | 141 |
| AEPD | 25 |
| SEPBLAC | 21 |
| BDE | 6 |
| ESMA | 4 |
| BDNS | 1 |
| CENDOJ | 1 |
| Registro oficial | 1 |

Screening lists:

| List | Rows |
| --- | ---: |
| `OFAC_SDN` | 19051 |
| `EU_SANCTIONS` | 5996 |

## Findings And Remediation

### F-01 Source Compliance Register Incomplete

Finding: `docs/reference/source-compliance-register.md` only described AEAT.

Impact: Source coverage could look complete without robots/licence/reuse/rate-limit notes for BOE, DGT, TEAC, CNMV, SEPBLAC, BDE, AEPD, BDNS, CENDOJ, EUR-Lex, ESMA, OFAC, EU sanctions, IRS/GIIN, CDI, PSD2 and PGC/XBRL.

Remediation: Expanded `docs/reference/source-compliance-register.md` into a source-family baseline. Domains that need legal/reuse review remain explicitly marked instead of silently accepted.

### F-02 Final Matrix Overclaimed Broad Families

Finding: rows such as `EUR-Lex / ESMA markets`, `MiCA / CASP`, and `Screening / sanctions` were too broad.

Impact: A reader could treat a loaded subfamily as full domain coverage.

Remediation: Split the matrix into subfamilies: EUR-Lex market acts, ESMA schemas/reporting, ESMA FIRDS/FITRS, MiCA CASP register, MiCA issuer workflows, OFAC, EU sanctions, UN/SEPBLAC/PEP screening, CDI, CRS/FATCA/GIIN, PSD2/SEPA, PGC/XBRL, and internal support surfaces.

### F-03 REST Surface Wider Than Accepted Product Surface

Finding: mounted REST routers include many broad regulatory/operational families not represented in the final matrix.

Examples: PBC, DORA, SFDR, CSRD, AIFMD, UCITS, CRD/BRRD/EMIR, MiFID, MAR, PRIIPs, DAC8, fraud, IRS/W-8, ownership, XBRL, playbooks, risk-control, AI governance and observability.

Impact: A mounted endpoint can look user-facing even when it is not accepted final source coverage.

Remediation: Matrix now marks those broad families as `out_of_scope` or `internal_support` unless a specific final product row accepts them.

### F-04 Final Gate Too Narrow

Finding: `final_product_acceptance_gate.py` covered 13 checks, while the plan required a broader final source gate.

Impact: BORME, BOE diario, BDNS, CENDOJ, CDI, PSD2 and GIIN were classified from inventory but not tested by the final gate.

Remediation: Gate expanded to more than 30 canonical checks, including BORME, BOE diario, BDNS, CENDOJ, CDI, PSD2, GIIN, BOE article/search, AEAT model/detail/casillas, doctrine search/list, CNMV list, EUR-Lex list, OFAC/EU screening and source manifest.

### F-05 Generic Source/Evidence Checks Were Too Weak

Finding: the gate treated any source-like key and generic `status` as sufficient.

Impact: a payload could pass with a non-official URL or a generic operational status.

Remediation: Gate now supports endpoint-specific official source host predicates and removed generic `status` from accepted evidence-status keys.

### F-06 BDNS And CENDOJ Lacked Explicit Coverage Metadata

Finding: BDNS and CENDOJ exposed traceable rows but lacked clear `coverage_status`, `safe_to_answer`, `row_completeness` and `row_provenance` in list responses.

Impact: very-limited sources could appear as ordinary affirmative lists.

Remediation: BDNS/CENDOJ list/detail responses now expose partial/very-limited/fail-closed metadata.

### F-07 HTTP MCP Did Not Expose All Final Matrix Document Corpora

Finding: BDE, BDNS, CENDOJ and SEPBLAC were mounted as REST routers but absent from `HTTP_MCP_OPERATIONS`.

Impact: final matrix described a transversal MCP/API product, but several final-source corpora were REST-only.

Remediation: added `listar/get` HTTP MCP operation ids for BDE, BDNS, CENDOJ and SEPBLAC.

### F-08 Source Manifest Is Not Full Source Inventory

Finding: `/v1/sources/manifest` parses only `docs/source-manifests/sociedad-valores-wave-1.md` and has metadata for six Wave 1 sources.

Impact: callers could mistake it for full source inventory.

Remediation: final matrix and compliance register now state that source manifest is `internal_support`, not a full inventory. Worker inventory remains the authoritative runtime worker map.

### F-09 Active Workers With Partial Status Are Expected But Must Not Be Overclaimed

Live `sync_log` shows:

- `worker-aepd` / `cron-aepd-weekly`: `partial`, `errors=0`, skipped AEPD URLs.
- `worker-aeat-modelos`: `partial`, `errors=0`, skipped AEAT resources.
- `worker-cnmv`: `partial`, `errors=0`, skipped CNMV documents.

These are not system failures, but they confirm the product must keep AEPD, AEAT and CNMV as partial unless a future source-specific sprint closes them.

## Source Families Audited

Accepted scoped/partial product families:

- AEAT modelos/current designs/BOE modelos
- BOE legislation
- BOE diario
- BORME
- DGT
- TEAC
- CNMV
- SEPBLAC
- BDE
- AEPD
- BDNS
- CENDOJ
- EUR-Lex
- EUR-Lex market
- ESMA MiFIR reporting
- ESMA FIRDS/DLT
- MiCA CASP
- OFAC SDN
- EU sanctions
- CDI/DTA
- GIIN/FATCA/IRS references
- PSD2/SEPA
- PGC/XBRL/ESEF
- Official regulatory references
- Regulatory watch/source revisions

Mounted but not accepted as final source coverage without a separate contract:

- DORA
- SFDR
- CSRD
- AIFMD/UCITS
- CRD/BRRD/EMIR
- MiFID/MAR/PRIIPs
- PBC full decisioning
- DAC8/fraud/consumer credit/insurance
- ownership/entity graph
- playbooks/risk-control/editorial/governance/observability

## Remaining Non-Blocking Risks

- Offsite backup/restore remains deferred by user decision.
- Some source compliance entries are marked `needs_legal_review`; this blocks broad redistribution claims, not the current internal/product functional closeout.
- `mcp_deep_contract_audit.py` remains stronger than the scheduled `mcp_validation_suite.py`; making it a recurring systemd gate is recommended as a follow-up hardening task.
