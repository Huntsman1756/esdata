# Source Compliance Register

Status: `SOURCE_AUDIT_BASELINE_2026_05_31`

Registro operativo de fuentes externas integradas o expuestas por `esdata`.

Este registro no concede permisos legales por si mismo. Sirve para que el producto no confunda una fuente oficial cargada con permiso ilimitado de reutilizacion, cobertura completa o estabilidad tecnica garantizada.

## Rules

- Preferir fuentes oficiales primarias.
- Mantener rate limiting/backoff por worker.
- No vender como completo un dominio parcial o muy limitado.
- No tratar un endpoint montado como producto aceptado si no aparece en `docs/final-product-coverage-matrix.md` con estado y limites.
- Si una fuente no tiene nota de licencia/robots verificada en este registro, su estado de compliance es `needs_legal_review` para expansion comercial o redistribucion masiva.

## Baseline

| Source family | Primary official domain(s) | Active worker / surface | Product state | Compliance status | Operational limits |
| --- | --- | --- | --- | --- | --- |
| AEAT modelos / Sede AEAT | `sede.agenciatributaria.gob.es`, `agenciatributaria.gob.es` | `worker-modelos`, `cron-modelos-daily`, `worker-aeat-current-designs`, `/v1/modelos` | `partial` | `known_constraints` | Public model pages/resources; JS/geography can affect scraping; use rate limit/backoff; do not assert campaign without direct official evidence. |
| BOE legislacion consolidada | `www.boe.es` | `worker-boe`, `cron-boe-daily`, `/v1/legislacion` | `usable_scoped` | `official_public_needs_reuse_review` | Use official BOE URLs/ELI/BOE ids; coverage is loaded corpus, not all Spanish law. |
| BOE diario / BORME / BOE datos abiertos | `www.boe.es` | `cron-boe-diario-daily`, `worker-borme`, `/v1/boe-diario`, `/v1/borme` | `partial` | `official_public_needs_reuse_review` | BORME extraction is heuristic/partial; BOE diario is non-consolidated and must not imply vigente consolidated law. |
| DGT / PETETE | `petete.tributos.hacienda.gob.es`, `sede.agenciatributaria.gob.es`, `hacienda.gob.es` | `worker-dgt`, `/v1/doctrina`, lineas de criterio | `partial_traceable` | `official_public_needs_reuse_review` | Query/search corpus is large but not a complete curated doctrine product; `safe_to_answer=false` blocks final answers. |
| TEAC / DYCTEA | `serviciostelematicosext.hacienda.gob.es`, `hacienda.gob.es` | `worker-teac`, `/v1/doctrina` | `partial_traceable` | `official_public_needs_reuse_review` | Used as doctrinal support only when exact evidence exists. |
| CNMV | `www.cnmv.es` | `worker-cnmv`, `cron-cnmv-weekly`, `/v1/cnmv` | `partial` | `official_public_needs_reuse_review` | Worker can be `partial` after skipped documents; `/v1/cnmv/coverage` distinguishes loaded/unavailable families. |
| SEPBLAC | `www.sepblac.es` plus BOE norms where applicable | `worker-sepblac`, `/v1/sepblac` | `partial` | `official_public_needs_reuse_review` | Documents/guides only; PBC/FT decisioning remains partial and review-based. |
| Banco de Espana | `www.bde.es` | `worker-bde`, `/v1/bde` | `partial` | `official_public_needs_reuse_review` | Very small corpus; no full banking-supervision claim. |
| AEPD | `www.aepd.es` | `worker-aepd`, `/v1/aepd` | `partial` | `official_public_needs_reuse_review` | Guides/documents only; no full sanctioning-resolution or GDPR compliance coverage. |
| BDNS | `www.infosubvenciones.es`, `pap.hacienda.gob.es` | `worker-bdns`, `/v1/bdns` | `very_limited` | `official_public_needs_reuse_review` | Minimal corpus; no broad subsidy coverage claim. |
| CENDOJ / Poder Judicial | `www.poderjudicial.es` | `worker-cendoj`, `/v1/cendoj` | `very_limited` | `official_public_needs_reuse_review` | Minimal/narrow loaded corpus; broad jurisprudence remains unavailable/target. |
| EUR-Lex / Publications Office | `eur-lex.europa.eu`, `op.europa.eu` | `worker-eurlex`, `worker-eurlex-market`, `/v1/eurlex`, `/v1/eurlex/market` | `partial_to_usable_by_subfamily` | `official_public_needs_reuse_review` | Use CELEX/source metadata; metadata-only records are not article text. |
| ESMA | `www.esma.europa.eu`, ESMA public registers/files | `worker-esma-*`, `/v1/esma/*`, `/v1/mica/casp` | `partial_to_usable_by_subfamily` | `official_public_needs_reuse_review` | CASP loaded is usable; FIRDS/FITRS/full datasets are not broad product coverage. |
| OFAC SDN | `sanctionslistservice.ofac.treas.gov`, `home.treasury.gov` | `cron-ofac-sdn-weekly`, `/v1/screening` | `usable_scoped` | `official_public_needs_reuse_review` | Loaded OFAC list only; no EU/UN/PEP inference. |
| EU sanctions / DG FISMA | `data.europa.eu`, `finance.ec.europa.eu` | `cron-eu-sanctions-weekly`, `/v1/screening` | `usable_scoped` | `official_public_needs_reuse_review` | Loaded EU FSF list only; no UN/SEPBLAC/PEP inference. |
| GIIN / IRS FATCA | `apps.irs.gov`, `irs.gov` | `cron-giin-monthly`, `/v1/irs-fiscal/giin` | `partial` | `official_public_needs_reuse_review` | GIIN registry lookup is not full FATCA/CRS procedure coverage. |
| CDI / DTA conventions | AEAT/Hacienda/BOE treaty sources | `worker-cdi`, `/v1/internacional/convenios` | `partial` | `official_public_needs_reuse_review` | Treaty metadata exists; no definitive withholding answer without article/rate/source validation. |
| PSD2 / SEPA | EBA/BDE/EPC or configured official references | `cron-psd2-weekly`, official references, `/v1/psd2` | `partial` | `needs_legal_review` | Public JSON source may be inaccessible; loaded data is narrow. |
| PGC / XBRL / ESEF | BOE, XBRL/ESEF official sources where configured | `cron-pgc-boe-monthly`, `/v1/pgc`, `/v1/xbrl` | `partial` | `needs_legal_review` | Not part of final source claim beyond narrow loaded records. |
| Official regulatory references | BOE/EUR-Lex/official source set per seed | `official-regulatory-references` | `internal_support` | `needs_legal_review_by_source` | Seeds support obligations and references; individual source rows still need domain-level evidence. |
| Regulatory watch | BOE/AEAT/DGT configured pages | `cron-regulatory-daily`, `source_revision` | `internal_support` | `needs_legal_review_by_source` | Change detection telemetry, not direct user-facing source corpus. |

## Known Non-Claims

- `source_manifest` currently covers the Wave 1 manifest only: CNMV, SEPBLAC, EUR-Lex, CENDOJ, BDE and AEPD. It is not the full ingestion inventory.
- Mounted REST routers for broad regulatory families are not automatically accepted product sources.
- Helper/dead workers listed in `docs/worker-inventory.md` must not be promoted without a new source, evidence, compliance and gate story.
- Backup/offsite restore is outside this source compliance register.
