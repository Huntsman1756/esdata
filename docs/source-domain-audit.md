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
| EUR-Lex | `norma`, `articulo`, `version_articulo` con `tipo_fuente='eurlex'` | `/v1/eurlex` devuelve 20 documentos; worker informa `fetch_articles=False`, `discovery_enabled=False` | `worker-eurlex` y `cron-eurlex-weekly` OK con `rows_processed=0` y sin errores | API responde; MCP ampliado con `listar_eurlex/get_eurlex` | Parcial: corpus curado disponible, descubrimiento live no activo |
| FATCA / GIIN | `giin_registry`, `irs_*`, modelo AEAT 290 | `giin_registry=508593`; `irs_dta_convention=92`; modelo 290 `casillas_total=152` | `cron-giin-monthly` OK 2026-05-11; `official-regulatory-references` OK | MCP ampliado con `listar_registros_giin/detalle_registro_giin`; endpoint GIIN paginado para no volcar 500k filas | Parcial: GIIN real masivo; modelo 290 sigue `verified=false`, `completeness=parcial` |
| CRS / DAC2 | modelo AEAT 289, `obligacion_internacional` | modelo 289 `casillas_total=7`; `obligacion_internacional=0` | Cubierto indirectamente por AEAT/current designs; no hay worker CRS independiente | API modelo 289 responde como evidencia limitada; `/v1/internacional/obligaciones` devuelve 0 | Parcial: no afirmar procedimiento CRS completo sin fuente adicional |
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
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=true`, 163 tablas, 56 FK, 90 tablas vacias clasificadas sin `unknown`, `expected_operations=63`, `tools_returned=63`.
