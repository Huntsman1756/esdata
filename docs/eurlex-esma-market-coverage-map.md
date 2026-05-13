# EUR-Lex + ESMA Market Coverage Map

Estado: E-00 completado para el sprint `esdata-eurlex-esma-markets`.

Fecha de corte: 2026-05-13.

Regla aplicada: este mapa solo inventaria fuentes oficiales y decide si son parseables. No carga datos, no crea tablas y no eleva ningun contrato a `verified=true`.

## Referencia De Calidad

Se toma como referencia el cierre AEAT en `docs/aeat-documentation-coverage-report.md`:

- `source_url` obligatorio por registro cargado.
- `source_hash` del fichero descargado cuando haya fichero.
- `capture_date` en cada carga.
- `verified=true` solo con datos estructurados completos para el alcance declarado.
- `verified=false` + `completeness=parcial` cuando solo haya metadata, XSD parcial, piloto o texto incompleto.
- `configured_but_unavailable` cuando el dominio esta definido pero no hay datos reales cargados.
- No se infieren campos, reglas, obligaciones ni textos desde prosa no estructurada.

## Estado Actual Observado En El Repositorio

| area | estado actual | gap principal |
|---|---|---|
| EUR-Lex general | Existe `apps/workers/eurlex.py` y router `/v1/eurlex`; MiFID II aparece validado en informes previos con articulado real. | No existe tabla dedicada `eurlex_act`/`eurlex_article` con contrato AEAT-like por CELEX de mercados. |
| MiFID II | `MIFID2_2014_65` ya fue validado en Q-06/Q-12 con texto real y CELEX `32014L0065`. | Reconciliar a nuevas tablas y verificar completitud articulo por articulo. |
| MiFIR | Hay referencias/vocabulario y worker CNMV clasifica documentos como `mifir`. | Falta articulado completo `32014R0600` en tabla dedicada y endpoints especificos. |
| MiCA | CASP ESMA esta cargado desde CSV oficial; tablas `crypto_asset`, `tokenized_asset`, `wallet_custodian`, `crypto_transaction` quedan fail-closed si no hay datos reales. | Falta articulado completo `32023R1114`; falta mapa de fuentes oficiales para emisores/tokens si ESMA/EBA publican datasets. |
| DLT Pilot | Hay referencias documentales, pero no tabla especifica de infraestructuras DLT autorizadas. | Falta articulado `32022R0858` y parser/listado ESMA de infraestructuras autorizadas. |
| FIRDS/FITRS | No se observan tablas `esma_firds_*` ni `esma_fitrs_result`. | Falta ingestion de metadata, esquemas y piloto de ficheros. |
| MiFIR transaction reporting | Hay vocabulario/micro-obligaciones, no `esma_schema` ni `esma_schema_field`. | Falta parsear XSD oficial ESMA y validaciones. |

## EUR-Lex Sources

| domain | official source | format | update/frequency notes | status | reason |
|---|---|---|---|---|---|
| MiFID II | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0065 | EUR-Lex HTML/XML text, CELEX `32014L0065` | EU act; amendments occur irregularly. Monthly hash check is enough. | STATUS-A | Official EUR-Lex text is parseable. Existing corpus already has real MiFID II article text, but E-02 must reconcile completeness and provenance in dedicated tables. |
| MiFIR | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32014R0600 | EUR-Lex HTML/XML text, CELEX `32014R0600` | Amended by later EU acts, including MiFIR review changes. Monthly hash check. | STATUS-A | Official regulation text is parseable and is the legal basis for FIRDS, FITRS and transaction reporting. |
| MiCA | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32023R1114 | EUR-Lex HTML/XML text, CELEX `32023R1114` | Recently applicable framework; check monthly and after ESMA/EBA technical standard updates. | STATUS-A | Official MiCA regulation text is parseable. CASP register is separate ESMA source. |
| DLT Pilot Regulation | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R0858 | EUR-Lex HTML/XML text, CELEX `32022R0858` | DLT Pilot can change by extension/permanent framework decisions. Monthly hash check. | STATUS-A | Official text is parseable; needed for DLT market infrastructure scope, exemptions and supervisory framework. |
| MAR | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32014R0596 | EUR-Lex HTML/XML text, CELEX `32014R0596` | Capital markets integrity act; amended irregularly. Monthly hash check. | STATUS-A | Official EUR-Lex text exists and should be included in the market-law baseline, even if later stories prioritize MiFIR/MiCA/DLT first. |

## ESMA Reporting And Registry Sources

| domain | official source | format | update/frequency notes | status | reason |
|---|---|---|---|---|---|
| MiFIR Reporting Hub | https://www.esma.europa.eu/data-reporting/mifir-reporting | ESMA HTML page linking instructions, schemas, validations and registers | Page changes when ESMA updates reporting instructions, schemas or validation rules. Weekly check. | STATUS-E | Source is official but requires link discovery and document-type classification before loading. |
| MiFIR Transaction Reporting XSD 1.1.0 | https://www.esma.europa.eu/document/transaction-reporting-xml-schema-110 | ESMA document page with ZIP of ISO 20022 XML schemas | Stable since 2019 but must be hash checked. | STATUS-A | ZIP/XSD is deterministic; parse `xs:element`, types and documentation only. |
| MiFIR Transaction Reporting instructions | https://www.esma.europa.eu/data-reporting/mifir-reporting | PDF/doc links from reporting hub | Updated when ESMA changes reporting instructions. Weekly discovery, manual parser classification. | STATUS-E | Metadata can be loaded safely; rule extraction only if structured. |
| MiFIR Transaction Reporting validation rules | https://www.esma.europa.eu/data-reporting/mifir-reporting | Linked document, likely XLS/PDF depending version | Updated periodically. Weekly discovery. | STATUS-E | If XLS/structured, load rule codes; if PDF prose, metadata only and `parcial`. |
| FIRDS reference data | https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_firds | ESMA register UI/API, FULINS/DLTINS XML/ZIP files | Daily files; full files can be very large. Daily metadata check. | STATUS-E | Load file metadata and one pilot delta only. Full FULINS requires capacity decision. |
| FITRS transparency data | https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_fitrs | ESMA register UI/API, transparency result files | File availability changes with transparency calculations and MiFIR review. Weekly/daily depending file type. | STATUS-E | Needs register-file discovery and schema-specific parser. |
| DLT Pilot Regime page | https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/dlt-pilot-regime | ESMA HTML page + linked documents/list | Low volume; check monthly. | STATUS-E | Page is official and includes/links authorised DLT infrastructure list; parser must inspect if list is structured. |
| Authorised DLT Market Infrastructures | https://www.esma.europa.eu/document/list-authorised-dlt-market-infrastructures | ESMA document/list page | Low volume; may be empty or sparse. Monthly check. | STATUS-E | If structured list exists, load infrastructure rows; if list is empty, publish `configured_but_unavailable` with source evidence. |
| ESMA MiCA CASP register | https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_mifid_ifregs | ESMA register; current worker discovers CASPS.csv from ESMA MiCA page | Live register; weekly refresh already configured. | STATUS-A | CASP data is already loaded from official ESMA CSV. E-09 should verify freshness/provenance and avoid claiming non-CASP MiCA tables are complete. |

## New Vs Existing Coverage

| item | existing coverage | target action |
|---|---|---|
| MiFID II articulado | Existing real article text in `norma/articulo`; Q-sprint validated CELEX `32014L0065`. | E-02/E-13 must reconcile count, source hash and dedicated market endpoint. |
| MiFIR articulado | Not dedicated. Vocab/micro-obligation references exist. | E-02 load full EUR-Lex text into market tables. |
| MiCA articulado | CASP register exists; MiCA legal text not dedicated. | E-03 load full EUR-Lex text. |
| DLT Pilot articulado | Not dedicated. | E-04 load full EUR-Lex text. |
| MAR articulado | Not in immediate E-02 to E-04 sequence, but source is STATUS-A. | Add follow-up if E-00 map is expanded or include in E-13 backlog. |
| ESMA transaction reporting schema | Not loaded as `esma_schema/esma_schema_field`. | E-05 parse XSD ZIP. |
| ESMA validation rules | Not loaded as structured rules. | E-06 metadata first; structured extraction only if safe. |
| FIRDS/FITRS | No dedicated tables in current schema. | E-07 pilot and later FITRS story. |
| DLT authorised infrastructures | No dedicated table. | E-08 load list or document zero-authorisation state. |
| CASP | Existing official ESMA CASP load, 192 unique records in prior audits. | E-09 verify and refresh. |

## E-00 Decisions

- E-01 must create schema before any loader work.
- EUR-Lex article loading should prefer XML/HTML from EUR-Lex and store the exact response hash.
- ESMA XSD is the authoritative source for transaction reporting fields; reporting instructions are secondary context.
- FIRDS full-load is explicitly out of scope for E-07. Only metadata and a bounded delta pilot are acceptable.
- DLT zero-authorisation is a valid outcome if ESMA source says no authorised infrastructures; it must be exposed as `configured_but_unavailable` or equivalent, not as failure.
- Non-CASP MiCA tables stay fail-closed until official structured source is mapped and loaded.

## Immediate Next Story

E-01: inspect current production schema (`\dt eurlex_* esma_* casp_*`), create Alembic migration for missing dedicated tables, apply to test DB first, then production. No data loading should happen before E-01 passes.
