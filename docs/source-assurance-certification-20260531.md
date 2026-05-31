# Source Assurance Certification - 2026-05-31

Status: `P0_5_SOURCE_ASSURANCE_BASELINE`

Scope: prevent catastrophic overclaims about source coverage. This document does
not add new product scope and does not certify any domain as complete.

## Executive Rule

No domain is certified as exhaustive. ESData is certified only as a scoped,
evidence-backed, fail-closed consultation system over the loaded and declared
corpus.

## Certification Classes

- `scoped_verified`: representative canaries pass with official source evidence,
  but coverage is still bounded by loaded corpus and endpoint contract.
- `partial_declared`: real data and source references exist, but coverage is
  incomplete and must stay in review mode for broad questions.
- `very_limited_declared`: narrow or tiny corpus exists; only exact loaded-record
  checks are allowed.
- `not_certified`: mounted code or historical data may exist, but no product
  claim is allowed.
- `internal_support`: operational telemetry or governance support, not a source
  coverage claim.

## Domain Certification Matrix

| Domain | Certification | Allowed Claim | Forbidden Claim |
| --- | --- | --- | --- |
| BOE legislation | `scoped_verified` | Loaded BOE norms/articles can be cited where endpoint returns BOE evidence. | Full Spanish legal corpus or every law/article. |
| AEAT models | `partial_declared` | Loaded model metadata, casillas, resources and campaign summaries can support review. | Complete Hacienda coverage, automatic filing obligations, or campaign assertions without direct official evidence. |
| DGT/TEAC doctrine | `partial_declared` | Loaded doctrine lines/documents can support review when `safe_to_answer` allows it. | Complete doctrine, binding answer, or all DGT/TEAC material. |
| CNMV | `partial_declared` | Loaded CNMV documents and coverage-family state can be reviewed. | Complete CNMV universe, all circulars, Q&A, registers or supervisory material. |
| BDE | `partial_declared` | Loaded Banco de Espana documents can be cited as partial corpus. | Complete banking-supervision coverage. |
| SEPBLAC | `partial_declared` | Loaded SEPBLAC documents/guides can be cited for review. | Full PBC/FT decisioning or complete SEPBLAC sanctions/screening. |
| AEPD | `partial_declared` | Loaded AEPD guides/documents can be cited as partial corpus. | Complete GDPR compliance or all sanctioning resolutions. |
| BORME / BOE diario | `partial_declared` | Loaded non-consolidated notices can be reviewed with BOE traceability. | Consolidated law status or complete BOE/BORME universe. |
| BDNS / CENDOJ | `very_limited_declared` | Narrow loaded-record checks only. | Broad subsidy or jurisprudence coverage. |
| EUR-Lex market acts | `scoped_verified` | Loaded CELEX/market-act records can be cited where article/source metadata is present. | Complete EU regulatory corpus. |
| ESMA MiFIR / DLT | `partial_declared` | Loaded schema/reporting/DLT records can support review. | Complete ESMA reporting or all ESMA datasets. |
| ESMA FIRDS/FITRS | `very_limited_declared` | Pilot or explicit fail-closed behavior only. | Full instrument universe or absence/presence conclusions. |
| MiCA CASP | `scoped_verified` | Loaded ESMA CASP register entries can be queried. | Complete MiCA or crypto-asset regulatory coverage. |
| OFAC / EU sanctions | `scoped_verified` | Loaded OFAC SDN and EU sanctions entries can be queried by list. | UN, SEPBLAC, PEP or all sanctions-risk coverage. |
| CDI / FATCA / GIIN / PSD2 / PGC / XBRL | `partial_declared` | Narrow loaded references can support inventory review only until row-level source provenance is exposed. | Complete international tax, payments, accounting or reporting engine. |
| DORA / SFDR / CSRD / AIFMD / UCITS / CRD / EMIR / MiFID / MAR / PRIIPs / PBC / fraud | `not_certified` | Treat as development or narrow operational surfaces unless a separate contract accepts them. | Final source coverage. |
| Source manifest / regulatory watch | `internal_support` | Freshness/change telemetry for configured sources. | Complete source inventory or user-facing legal-change corpus. |

## Forbidden Product Claims

- ESData covers all Hacienda, BOE, CNMV, BDE, ESMA or EUR-Lex material.
- ESData contains all laws, all models, all regulations, all circulars or all
  sanctions sources.
- Empty search results prove that an obligation, sanction, law, circular or
  regulatory source does not exist.
- A mounted REST endpoint is accepted product coverage by itself.
- A partial corpus can be used for automatic fiscal, legal, sanctions or
  regulatory decisions.

## Canary Gate Coverage

The current gates must remain green together:

- `scripts/maintenance/final_product_acceptance_gate.py`: 30 canonical checks
  across health, BOE, AEAT, doctrine, CNMV, EUR-Lex, MiCA, screening, AEPD,
  SEPBLAC, BDE, BORME, BOE diario, BDNS, CENDOJ, CDI, PSD2 and GIIN.
- `scripts/maintenance/mcp_validation_suite.py`: read-only semantic smoke.
- `scripts/maintenance/mcp_deep_contract_audit.py`: DB registry, FK, domain
  availability, MCP/OpenAPI parity and semantic contracts.
- `scripts/maintenance/source_assurance_gate.py`: static anti-overclaim and
  source certification guard.

Current inventory-only canaries for CDI, PSD2 and GIIN do not certify final
answer quality because their representative list payloads do not yet expose
row-level source URL/hash/capture metadata. They remain useful for inventory
navigation, not for definitive conclusions.

If any gate fails, the correct state is not "product complete"; it is blocked
or partial until the failure is explained and fixed.

## Residual Risk

Backup/offsite restore remains outside this source-assurance baseline by prior
user decision. Legal/reuse review remains required before broad redistribution
or commercial licence claims for source corpora.
