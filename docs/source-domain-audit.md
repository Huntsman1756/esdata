# Non-AEAT Source Domain Audit

Fecha: 2026-05-12
Entorno verificado: VPS `212.227.227.64`, Docker Compose en `/srv/esdata`.

Este documento replica el criterio aplicado a modelos AEAT: una fuente queda marcada como cubierta solo si hay datos reales, worker/job observado, endpoint/API consultable y contrato MCP/API que no inventa cuando la evidencia es limitada.

## Estado Por Fuente

| Fuente / dominio | Tablas principales | Datos reales observados | Worker/job observado | API/MCP | Estado |
| --- | --- | ---: | --- | --- | --- |
| BOE legislacion | `articulo`, `version_articulo`, `norma` | `articulo=969`, `version_articulo=2252`, `norma=37` | `worker-boe` OK 2026-05-12 07:05-07:09 UTC; `cron-boe-daily` puede devolver `partial` si hay lock activo | API y MCP `get_articulo`/`buscar` validados previamente; citas BOE preservadas | Cubierto para corpus BOE cargado |
| BORME | `documento_interpretativo`, `source_revision` | `borme=1`, `source_revision=1` | `worker-borme` y `cron-borme-weekly` OK | Se detecto router no montado; corregido para exponer `/v1/borme` y MCP `listar_borme/get_borme` | Cubierto tras despliegue del fix |
| CNMV | `documento_interpretativo`, `documento_cnmv_version`, `cnmv_regulation_link`, `cnmv_obligation_link` | `cnmv=72`, `documento_cnmv_version=72`, `regulation_link=155`, `obligation_link=47` | `worker-cnmv` y `cron-cnmv-weekly` OK | `/v1/cnmv` responde; MCP ampliado con `listar_cnmv/get_cnmv/*links/*versions` | Cubierto para circulares/documentos cargados desde fuente oficial BOE/CNMV |
| EUR-Lex | `norma`, `articulo`, `version_articulo` con `tipo_fuente='eurlex'` | `norma=32`; tras ingesta acotada S-06: `articulo=93`, `version_articulo=93` para MiFID II (`32014L0065`); el resto de CELEX puede seguir `metadata_only` | `worker-eurlex` y `cron-eurlex-weekly` OK; S-06 ejecutado con `EURLEX_FETCH_ARTICLES=true`, `EURLEX_ONLY_CELEX=32014L0065`, `EURLEX_MAX_CELEX_PER_RUN=1`; S-09 anade counters por CELEX | API/MCP `listar_eurlex/get_eurlex` responde con `coverage_status`, `verified`, `completeness`, `articulos_total`, `articles_expected`, `articles_parsed`, `quality_status`, `evidence_notice`; MiFID II queda `article_text_available` y otros registros sin articulado quedan `evidence_limited` | Parcial-controlado: articulado real cargado por CELEX allowlisted; no se afirma cobertura exhaustiva EUR-Lex sin revisar counters y fuente citada |
| FATCA / GIIN | `giin_registry`, `irs_*`, modelo AEAT 290, `obligacion_internacional` | `giin_registry=508593`; `irs_dta_convention=92`; modelo 290 `casillas_total=152`; referencias FATCA oficiales cargadas por `official-regulatory-references` | `cron-giin-monthly` OK 2026-05-11; `official-regulatory-references` OK | MCP ampliado con `listar_registros_giin/detalle_registro_giin` y `listar_obligaciones_internacionales/detalle_obligacion_internacional`; endpoint GIIN paginado | Parcial-controlado: GIIN real masivo y fuentes BOE para FATCA/modelo 290; modelo 290 sigue `verified=false`, `completeness=parcial` para no afirmar procedimiento completo |
| CRS / DAC2 | modelo AEAT 289, `obligacion_internacional` | modelo 289 `casillas_total=7`; referencias oficiales `CRS`, `CRS_RD_1021_2015`, `MODELO_289_CRS`, `DAC2_2014_107_UE` cargadas con fuente BOE/EUR-Lex | `official-regulatory-references` carga referencias normativas; AEAT/current designs cubre campos parciales | API modelo 289 responde como evidencia limitada; `/v1/internacional/obligaciones` queda poblado y trazado con `source_url` | Parcial-controlado: fuentes normativas consultables; no afirmar obligatoriedad/casos concretos sin evidencia del supuesto |
| ESMA / MiCA | `casp`, tablas MiCA workflow | `casp=192`; `crypto_asset/tokenized_asset/wallet_custodian/transactions=0` | `cron-mica-weekly` OK | `/v1/mica/casp` responde; endpoints vacios devuelven availability `configured_but_unavailable` | Cubierto para CASP ESMA; resto MiCA fail-closed |
| PSD2 / SEPA | `psd2_aspsp`, `psd2_aisp`, `psd2_pisp`, `sepa_payment_rule` | `aspsp=5`, `aisp=3`, `pisp=3`, `sepa_payment_rule=2` | `cron-psd2-weekly` OK con aviso `eba_euclid_spa_not_accessible_public_json_endpoint` | API responde; MCP ampliado con list/get ASPSP/AISP/PISP/SEPA | Parcial: datos base presentes; EBA EUCLID publico no accesible como JSON |
| BDE / SEPBLAC / AEPD / CENDOJ / BDNS / DGT / TEAC | `documento_interpretativo`, `source_revision`, `dgt_queue` | DGT `18631`, TEAC `10`, BDE `2`, SEPBLAC `2`, AEPD `1`, CENDOJ `1`, BDNS `1` | workers y crons OK en `sync_log` | Doctrina/search existentes; availability evita afirmar dominios vacios | Cubierto para filas cargadas; ampliar corpus queda como backlog por fuente |
| Screening / sanctions | `screening_lists`, `screening_entries` | `screening_lists=3`, `screening_entries=18959` | `cron-ofac-sdn-weekly` OK | `/v1/screening/entries` responde; si se pide EU/UN/SEPBLAC/PEP sin datos, devuelve `configured_but_unavailable` | Parcial: OFAC cargado; EU/UN/SEPBLAC/PEP fail-closed |

## Gaps Criticos Cerrados En Esta Iteracion

- BORME existia como worker/router, pero `main.py` no montaba `borme.router`; por tanto OpenAPI/API/MCP no lo exponian. Se corrige.
- `BORMEDetail` y `BORMEListResponse` no existian en `schemas.py`; montar el router fallaba en import. Se anaden schemas compatibles con el payload real.
- GIIN/FATCA tenia 508.593 filas y el endpoint `/v1/irs-fiscal/giin` no paginaba. Se anaden `limit`, `offset`, `has_more` y `next_offset` antes de exponerlo al MCP.
- BORME, EUR-Lex, PSD2 ASPSP/AISP/PISP y SEPA quedan acotados con `limit/offset` antes de exponerlos al MCP para evitar respuestas no acotadas si el corpus crece.
- MCP HTTP no exponia herramientas directas para varias fuentes oficiales no-AEAT ya cargadas. Se amplian `HTTP_MCP_OPERATIONS` con fuentes de solo lectura: BORME, CNMV, EUR-Lex, GIIN/IRS, internacional, MiCA CASP, PSD2/SEPA y screening entries.
- `obligacion_internacional` estaba vacia en produccion aunque los tests locales sembraban FATCA/CRS. Se mueve el contenido base a `official-regulatory-references` con fuentes oficiales: BOE-A-2014-6854, BOE-A-2014-6922, BOE-A-2015-12399, BOE-A-2016-9834, EUR-Lex 32014L0107 y EUR-Lex 32018L0822. El endpoint internacional expone `source_url`, `source_worker` y paginacion.
- Revision de MCP externos (`EU_compliance_MCP` y `anamtb/boe-mcp`) registrada en `docs/reference-mcp-code-review.md`. Decision aplicada: EUR-Lex metadata-only ya no se devuelve como texto vacio silencioso; API/MCP expone `metadata_only`, `verified=false`, `completeness=parcial` y `evidence_notice`.

## Contrato De Verdad

- `populated`: se puede responder solo con filas y procedencia devueltas.
- `workflow_empty`: tabla operacional o de workflow; no se debe inventar actividad.
- `allowed_empty`: vacia por configuracion/runtime aceptable.
- `configured_but_unavailable`: fuente prevista pero sin filas verificadas; el MCP/API debe explicitar falta de cobertura.
- `partial`: hay evidencia oficial parcial; el agente debe decir `evidencia limitada` y no afirmar obligatoriedad ni procedimiento completo.

## Evidencia Freshness / Gates

- `/status`: API OK, DB OK, `stale_workers=0`.
- Probes VPS tras despliegue `b2cc8812`:
  - `/v1/borme?limit=1&offset=0`: `200`, `total=1`, `actos_len=1`.
  - `/v1/eurlex?limit=2&offset=0`: `200`, `total=32`, `documentos_len=2`, `has_more=true`.
  - `/v1/irs-fiscal/giin?limit=3&offset=0`: `200`, `total=508593`, `registros_len=3`, `next_offset=3`.
  - `/v1/psd2/aspsp?limit=2`, `/aisp?limit=2`, `/pisp?limit=2`: `200`, respuestas paginadas.
  - `/v1/psd2/sepa-rules?limit=1`: `200`, `total=2`, `has_more=true`.
  - `/v1/screening/entries?codigo=EU_SANCTIONS`: `configured_but_unavailable`, `safe_to_answer=false`.
- `mcp_validation_suite.py --read-only --base-url http://api:8000`: `ok=true`, `tool_count=63`.
- `S-04` FATCA/CRS: `official-regulatory-references` cargó 9 filas en `obligacion_internacional`; SQL confirma fuentes `boe.es`/`eur-lex.europa.eu` en `source_revision`; `/v1/internacional/obligaciones?limit=3` devuelve `total=9` con paginacion y `source_url`; `/v1/internacional/obligaciones/FATCA` devuelve `tipo=referencia_normativa` y fuente `BOE-A-2014-6854`.
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=true`, 163 tablas, 56 FK, 89 tablas vacias clasificadas sin `unknown`, `expected_operations=63`, `tools_returned=63`; resumen registry tras `S-04`: `populated=74`, `workflow_empty=53`, `allowed_empty=3`, `configured_but_unavailable=33`.
- Test local del contrato EUR-Lex: `PYTHONPATH=.;apps;apps/api;apps/workers python -m pytest apps/api/tests/test_eurlex_router.py -q --basetemp .pytest-tmp` -> `21 passed`. `ruff check apps/api/routers/eurlex.py apps/api/tests/test_eurlex_router.py --select F,I` -> `All checks passed`.
- VPS tras `S-05`: commit `3b75efe` desplegado; `/v1/eurlex?limit=1` devuelve `coverage_status=metadata_only`, `verified=false`, `completeness=parcial`, `articulos_total=0` y `evidence_notice` con `evidence_limited`; `mcp_validation_suite.py --read-only --base-url http://api:8000` -> `ok=true`.
- VPS tras `S-06`: commit `ad47498a` desplegado; `cron-eurlex-weekly` reconstruido y ejecutado con presupuesto acotado `EURLEX_ONLY_CELEX=32014L0065`, `EURLEX_MAX_CELEX_PER_RUN=1`; `sync_log` devuelve `status=ok`, `rows_processed=93`, `fetch_errors=0`, `fetch_articles=True`, `seed_selected=1`; SQL confirma `articulo=93`, `version_articulo=93` para `tipo_fuente='eurlex'`; `/v1/eurlex/MIFID2_2014_65` devuelve `coverage_status=article_text_available`, `verified=true`, `completeness=parcial`, `articulos_total=92`; `mcp_validation_suite.py --read-only --base-url http://api:8000` -> `ok=true`.
- VPS tras `S-08`: commit `fafed16` desplegado y API reconstruida; `mcp_validation_suite.py --read-only --base-url http://api:8000` -> `ok=true`; `mcp_deep_contract_audit.py --base-url http://api:8000` -> `ok=true`, `mcp_tools_contract.warning_count=0`, `tools_returned=63`, `expected_operations=63`.
