# EUR-Lex + ESMA Markets Coverage Report

Fecha: 2026-05-13

Este informe cierra el sprint `esdata-eurlex-esma-markets`. La regla aplicada es la misma que en AEAT: fuente oficial, trazabilidad por `source_url` + `source_hash` + `capture_date`, y contratos honestos cuando la cobertura es parcial.

## Resumen

| domain | source | records_loaded | verified | completeness | notes |
|---|---|---:|---|---|---|
| MiFID II articulado | EUR-Lex / EU Publications Cellar `32014L0065` | 92 articles | true | completa | Texto completo cargado en `eurlex_article`; endpoint `/v1/eurlex/market/32014L0065/articulos/{n}`. |
| MiFIR articulado | EUR-Lex / EU Publications Cellar `32014R0600` | 93 articles | true | completa | Texto completo cargado; artículo 1 validado por suite. |
| MiCA articulado | EUR-Lex / EU Publications Cellar `32023R1114` | 149 articles | true | completa | Texto completo cargado; artículo 1 validado por suite. |
| DLT Pilot articulado | EUR-Lex / EU Publications Cellar `32022R0858` | 19 articles | true | completa | Texto completo cargado; artículo 1 validado por suite. |
| ESMA MiFIR transaction reporting schema | ESMA MiFIR reporting XML Schema 1.1.0 | 1 schema, 168 fields | true | completa | Campos extraídos del XSD oficial; no se infieren campos desde prosa. |
| ESMA validation rules | ESMA structured validation rules workbook | 223 rules | true | completa | Solo reglas estructuradas parseables; PDFs MiFIR siguen como metadata. |
| ESMA reporting documents | ESMA MiFIR/DLT official pages and files | 5 documents | partial by document | parcial/completa by source | Documentos PDF no estructurados quedan metadata-only. |
| FIRDS file list | ESMA FIRDS register | 14 DLTINS files | false | parcial | Metadata reciente cargada; full FULINS queda fuera por volumen. |
| FIRDS instruments | ESMA FIRDS register payloads | 0 instruments | false | parcial | Instrument-level ISIN data is intentionally not loaded; ESData keeps only file metadata plus ESMA schemas/manuals/reporting documents. |
| DLT authorised infrastructures | ESMA DLT Pilot official PDF | 6 infrastructures, 75 exemptions | true | completa | Lista oficial parseada y validada contra texto fuente. |
| CASP register | ESMA interim MiCA CASP CSV | 192 verified CASP rows | true | completa | Registro oficial ESMA con `source_url`, `source_hash`, `capture_date`. |
| FITRS transparency results | ESMA FITRS register | 0 | false | configured_but_unavailable | Tabla creada y registrada; ingestion estructurada queda pendiente. |

## Contratos API

Los endpoints nuevos exponen `verified`, `completeness` y `quality_signal`:

| endpoint | contrato |
|---|---|
| `/v1/eurlex/market/acts` | `verified=true`, `completeness=completa` cuando devuelve actos cargados desde EUR-Lex/Cellar. |
| `/v1/eurlex/market/{celex}/articulos/{numero}` | Texto real oficial; falla 404 si el artículo no existe. |
| `/v1/esma/mifir/schemas` | `official_esma_schema`, completo para el XSD cargado. |
| `/v1/esma/mifir/transaction-reporting/fields` | `official_esma_xsd`, completo para los campos del XSD. |
| `/v1/esma/firds/files` | `verified=false`, `completeness=parcial`, `official_esma_file_metadata`. |
| `/v1/esma/firds/instruments?isin=...` | Siempre `safe_to_answer=false`; los ISIN reales no se cargan por decision de alcance. |
| `/v1/esma/dlt/infrastructures` | `official_esma_dlt_register` si la lista oficial tiene filas; si no, `configured_but_unavailable`. |
| `/v1/mica/casp/buscar` | `official_esma_register` para CASP cargados desde ESMA. |

## Jobs y frescura

| worker | schedule | status |
|---|---|---|
| `worker-eurlex-market` | monthly | `sync_log` fresh, `stale=false`, `cadence_declared=true`. |
| `worker-esma-mifir-reporting` | weekly | `sync_log` fresh, `stale=false`, `cadence_declared=true`. |
| `worker-esma-firds` | daily | `sync_log` fresh, `stale=false`, `cadence_declared=true`. |
| `worker-esma-dlt` | weekly | `sync_log` fresh, `stale=false`, `cadence_declared=true`. |

## Verificacion final

- `mcp_validation_suite.py --read-only --base-url http://api:8000`: `ok=true`.
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=true`.
- `/status`: `api=ok`, `database=ok`, all listed workers `stale=false`.
- Alertmanager: active alerts response is empty (`[]`).
- `table-remediation-registry.json`: 175 live tables registered; registry drift resolved.

## Limites conocidos

- Product decision: ESMA market coverage prioritizes current official reporting schemas, validation rules, RTS/ITS metadata, and regulatory text. It does not aim to replicate ESMA reference-data datasets.
- FIRDS full historical FULINS ingestion is intentionally out of scope. It is a capacity and product decision, not a bug. Loading it would require a separate storage estimate, partitioning strategy, retention policy, and operational budget.
- FIRDS instrument payloads (including bounded DLTINS samples) are intentionally out of scope. The MCP should use ESMA schemas, manuals, reporting documents and file metadata, not real ISIN-level FIRDS rows.
- FITRS transparency results are registered but not populated.
- ESMA prose PDFs are stored as document metadata unless a structured table/workbook/schema is available.
- Transaction reporting fields come from XSD definitions. RTS/prose interpretation is not inferred unless a structured official source provides it.
- EUR-Lex source URLs may be EU Publications Cellar URLs (`publications.europa.eu`), which are official EU publication sources.
