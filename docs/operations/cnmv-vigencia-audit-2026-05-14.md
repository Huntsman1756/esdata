# CNMV Vigencia Audit - 2026-05-14

## Production Snapshot

`documento_interpretativo` rows where `organismo_emisor='CNMV'` and `tipo_fuente='cnmv'`:

| estado_vigencia | documents | with documento_version |
|---|---:|---:|
| derogado | 30 | 30 |
| vigente | 19 | 19 |
| vigente_modificado | 23 | 23 |

Default `/v1/cnmv/buscar?q=circular&limit=100` before this change returned mixed states:

| estado_vigencia | returned |
|---|---:|
| derogado | 27 |
| vigente_modificado | 22 |
| vigente | 16 |

## Contract Decision

CNMV retrieval now treats current obligations as the default use case:

- default: `vigente` + `vigente_modificado`
- explicit historical audit: `vigencia=all`
- explicit deprecated-only audit: `vigencia=derogado`

Every list response exposes:

- `vigencia_filter`
- `included_estados_vigencia`
- `coverage_note`

The coverage note is intentional: the CNMV corpus is the official corpus loaded in ESData, not the full CNMV universe. A no-result response can mean "not loaded", not "does not exist".

## Remaining Risk

All 23 `vigente_modificado` documents have at least one `documento_version` row, but this does not by itself prove that the loaded text is the BOE consolidated text.

Follow-up hardening is tracked in `docs/operations/cnmv-consolidation-audit-2026-05-14.md`: version tables now expose explicit consolidation audit metadata (`es_consolidado`, `consolidated_verification_status`, checked URL, checked timestamp and evidence note). Agents must not treat a version row as consolidated unless `es_consolidado=true` and the verification status is `consolidated`.
