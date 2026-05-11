# Referencia de endpoints

## Objetivo

Este capitulo no sustituye OpenAPI. Sirve como mapa rapido de que exponer y para que usar cada bloque.

## Estado y salud

- `GET /health` — salud basica de la API y conectividad con DB
- `GET /status` — estado agregado de workers, freshness y modelos; por worker expone `stale`, `rows_processed`, `errors` y `duration_ms` como contrato operativo minimo
- `GET /metrics` — metricas, solo si la integracion esta activa
- `GET /v1/observability/dashboard` — panel JSON minimo con resumen de consulta, workers y fuentes
- `GET /v1/observability/alerts` — alertas operativas derivadas del estado actual sin depender de revision manual
- `GET /v1/domain-availability` — disponibilidad explicita de dominios/tablas
- `GET /v1/domain-availability/{table}` — disponibilidad de una tabla concreta
- `GET /v1/sources/manifest` — manifiesto vivo de fuentes con owner, trust tier, cadencia y deteccion de cambios
- `GET /v1/sources/freshness` — ledger de freshness por fuente con `snapshot_at`, `snapshot_version`, `previous_snapshot_at` y senal `changed_since_previous`
- `GET /v1/sources/freshness-alerts` — alertas de frescura

Gate operativo recomendado:

- `scripts/maintenance/mcp_validation_suite.py --read-only` para monitorizacion horaria ligera.
- `scripts/maintenance/mcp_deep_contract_audit.py` para validacion amplia antes de release/despliegue: tablas vivas, relaciones FK, disponibilidad por dominio, contrato MCP `tools/list`, GPT Actions OpenAPI y suite semantica fail-closed. Es read-only y respeta `Retry-After` si la API aplica rate limiting.

## Busqueda y legislacion

- `GET /v1/consulta` — consulta fiscal agregada con resultados, relevancia, confianza y score de faithfulness
- `GET /v1/buscar` — busqueda principal sobre legislacion consolidada unicamente; no devuelve modelos tributarios
- `GET /v1/legislacion/buscar` — alias funcional de la busqueda legislativa
- `GET /v1/legislacion/buscar/hybrid` — busqueda hibrida con peso vectorial configurable
- `GET /v1/legislacion` — listado de normas
- `GET /v1/legislacion/cobertura` — recuento de articulos y versiones por norma
- `GET /v1/legislacion/{codigo}` — detalle de una norma
- `GET /v1/legislacion/{codigo}/articulos` — listado de articulos de una norma
- `GET /v1/legislacion/{codigo}/articulos/{numero}` — detalle de articulo, con `vigente_en` opcional
- `GET /v1/legislacion/{codigo}/articulos/{numero}/historial` — historial de versiones de un articulo

Uso recomendado:

- usa `consulta` cuando quieras una respuesta agregada sobre modelos, obligaciones, normativa y doctrina con senal resumida de confianza
- usa `buscar` para descubrimiento inicial de legislacion
- usa `modelos` o `consulta` cuando la pregunta sea sobre modelos AEAT como `303`, `349` o `100`
- usa `get_norma` y `get_articulo` para detalle trazable
- usa `historial` cuando importe el estado historico de un articulo

## Doctrina

- `GET /v1/doctrina/buscar` — busqueda de doctrina por texto
- `GET /v1/doctrina/buscar/hybrid` — busqueda hibrida sobre doctrina
- `GET /v1/doctrina/{referencia}` — detalle de un documento doctrinal

Filtros utiles:

- `tipo`
- `desde`
- `organismo_emisor`

## Materias

- `GET /v1/materias`
- `GET /v1/materias/{slug}`

Uso recomendado:

- navegacion por taxonomia o agrupacion tematica

## Modelos AEAT

- `GET /v1/modelos` — listado resumido
- `GET /v1/modelos/campanas-operativas` — vista agregada de varios modelos
- `GET /v1/modelos/por-supuesto` — clasifica modelos AEAT candidatos para un supuesto fiscal; no marca modelos como obligatorios sin evidencia explicita
- `GET /v1/modelos/{codigo}` — detalle completo del modelo
- `GET /v1/modelos/{codigo}/articulos`
- `GET /v1/modelos/{codigo}/casillas` — pagina por defecto `limit=200`, maximo `500`; soporta `offset`, `q`, `tipo_casilla` y `pagina`
- `GET /v1/modelos/{codigo}/claves`
- `GET /v1/modelos/{codigo}/instrucciones`
- `GET /v1/modelos/{codigo}/normativa`
- `GET /v1/modelos/{codigo}/artefactos`
- `GET /v1/modelos/{codigo}/resumen-operativo`
- `GET /v1/modelos/{codigo}/campana-operativa`
- `GET /v1/modelos/{codigo}/fuentes-oficiales`

Uso recomendado:

- usa `/{codigo}` cuando quieras una vista completa
- usa `/por-supuesto` cuando el agente pregunte por modelos aplicables a un perfil, por ejemplo `sociedad_valores` con clientes residentes/no residentes; tratar `candidato` como no obligatorio hasta verificacion humana/oficial
- usa endpoints especializados cuando necesites payload mas pequeno o UI mas focalizada
- para listas grandes, pide `limit` y continua solo si `has_more=true` usando `next_offset`; no trates una pagina como listado completo
- en `/casillas`, `classification=confirmado` confirma que la casilla/campo existe en el modelo/campana devuelto, no que sea obligatoria para un supuesto concreto

Glosario de clasificacion:

- `confirmado`: hay evidencia explicita suficiente para afirmar la aplicabilidad indicada o la existencia del registro consultado
- `candidato`: coincidencia plausible, no obligatoria; requiere revision antes de operacionalizar
- `requiere_verificacion`: evidencia insuficiente o ambigua; no debe usarse para responder como hecho

## Convenios DTA y retenciones internacionales

- `GET /v1/internacional/convenios` — listado de convenios DTA con filtros por `pais_a`, `pais_b`, `estado` y `tipo_acuerdo`
- `GET /v1/internacional/convenios/{codigo}` — detalle de un convenio DTA
- `GET /v1/internacional/convenios/retenciones` — listado de reglas de retencion por tipo de renta y pais
- `GET /v1/internacional/convenios/retenciones/{codigo}` — detalle de una regla de retencion
- `POST /v1/internacional/convenios/retencion` — calculo cruzado de retencion aplicable segun pais de residencia, tipo de renta y convenio DTA vigente

Uso recomendado:

- usa `convenios` para explorar cobertura efectiva por pais en la instancia actual
- usa `retenciones` para inspeccionar la regla base por tipo de renta
- usa `retencion` cuando necesites la respuesta operativa final con `tipo_retencion_aplicable`, `tiene_convenio_dta`, `codigo_convenio` y `formulario_recomendado`

## Obligaciones, cambios y compliance

- `GET /v1/obligaciones`
- `GET /v1/obligaciones/aplicables`
- `GET /v1/obligaciones/operativas`
- `GET /v1/obligaciones/deadlines`
- `GET /v1/obligaciones/{codigo}`
- `GET /v1/cambios`
- `GET /v1/compliance/workflow`

Uso recomendado:

- `aplicables` para perfilado regulatorio rapido
- `operativas` para preguntas accionables de plazos, sanciones y triggers
- `workflow` para ver el estado de casos internos
- `cambios` para vigilancia y panel operativo

## Empresas, entidades y screening

- `GET /v1/empresas`
- `GET /v1/empresas/{empresa_id}`
- `GET /v1/entidades/lei/{lei}`
- `GET /v1/entidades/buscar`
- `GET /v1/entidades/{empresa_id}`
- `POST /v1/screening/`
- `GET /v1/screening/entries`
- `GET /v1/screening/matches/{empresa_id}`

Uso recomendado:

- `entidades` para resolucion y lookup de identidad
- `screening` para evaluacion de listas y coincidencias explicables

## PGC

- `GET /v1/pgc/cuentas`
- `GET /v1/pgc/buscar`
- `GET /v1/pgc/normas-valoracion`
- `GET /v1/pgc/estados-financieros`
- `GET /v1/pgc/referencias-fiscales`
- `GET /v1/pgc/referencias-aeat`

Uso recomendado:

- consulta contable y referencias auxiliares, no calculo fiscal automatico

## XBRL y reporting estructurado

- `GET /v1/xbrl/facts`
- utilidad: consultar facts XBRL persistidos por entidad y concepto en el slice inicial de reporting estructurado
- `GET /v1/xbrl/filings/{filing_id}`
- utilidad: obtener metadata completa de un filing XBRL y la lista de facts asociados
- estado actual: MVP fixture-first con XBRL local; sin iXBRL remoto y sin taxonomias completas

## Bancario utilitario (Fase 17)

- `POST /v1/banking/iban/validate`
- utilidad: validar IBAN (formato + mod-97 + longitud por pais) sin persistencia
- `GET /v1/banking/iban/countries`
- utilidad: listar codigos de pais soportados para validacion de longitud
- estado actual: endpoints stateless, sin DB, sin parsing ISO 20022

## Fuentes documentales adicionales

- `GET /v1/cnmv`
- `GET /v1/cnmv/{referencia}`
- `GET /v1/cendoj`
- `GET /v1/cendoj/{referencia}`
- `GET /v1/eurlex`
- `GET /v1/eurlex/{referencia}`
- `GET /v1/bde`
- `GET /v1/bde/{referencia}`
- `GET /v1/aepd`
- `GET /v1/aepd/{referencia}`

## Gobernanza AI (AI Act compliance)

- `GET /v1/ai/audit-log` — auditoria de decisiones AI (filtrado por fecha/componente)
- `GET /v1/ai/audit-log/{request_id}` — log completo de una peticion
- `GET /v1/ai/models` — registry de modelos IA registrados y versions
- `GET /v1/ai/models/active` — modelo activo
- `GET /v1/ai/config/current` — configuracion AI activa
- `GET /v1/ai/config/history` — historial de configuraciones
- `GET /v1/data/lineage` — lineage y calidad de datos por tabla/campo
- `GET /v1/data/quality` — score de calidad por tabla
- `GET /v1/data/catalog` — catalogo completo de fuentes y tablas trazadas
- `GET /v1/data/catalog/{tabla}` — catalogo de una tabla concreta
- `GET /v1/ai/human-review/pending` — revisiones humanas pendientes
- `GET /v1/ai/human-review/stats` — estadisticas de revision humana
- `GET /v1/ai/human-review/by-status/{status}` — revisiones por estado
- `GET /v1/ai/human-review/by-request/{request_id}` — revisiones por request id
- `GET /v1/ai/human-review/{review_id}` — detalle de revision humana
- `POST /v1/ai/human-review/{review_id}/decide` — aprobar/rechazar/modificar revision
- `POST /v1/ai/human-review/check` — evaluar si una respuesta requiere revision humana

Uso recomendado:

- `audit-log` para trazabilidad de decisiones AI ante reguladores
- `human-review` para flujos de supervision humana en consultas criticas
- `ai/models` para verificar version y configuracion del modelo en uso
- `data/lineage` y `data/quality` para auditoria de origen y calidad de datos

Nota de estado: routers para `/v1/bdns`, `/v1/borme`, `/v1/sepblac`,
`/v1/modelos/calendario`, `/v1/chunks`, `/v1/connectivity`, `/v1/irs/modelos`,
`/v1/ai/risk`, `/v1/ai/safety`, `/v1/ai/fairness-report`, `/v1/gdpr` y
`/v1/ai/xai` existen en el repositorio, pero no estan montados en la app runtime
v1.0. Tratar esos bloques como `configured_but_unavailable` o backlog hasta que
pasen OpenAPI, MCP y tests.

## Referencias

- `../../apps/api/main.py`
- `../../apps/api/routers/`
- `../openapi-gpt.json`
