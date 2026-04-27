# Referencia de endpoints

## Objetivo

Este capitulo no sustituye OpenAPI. Sirve como mapa rapido de que exponer y para que usar cada bloque.

## Estado y salud

- `GET /health` — salud basica de la API y conectividad con DB
- `GET /status` — estado agregado de workers, freshness y modelos; por worker expone `stale`, `rows_processed`, `errors` y `duration_ms` como contrato operativo minimo
- `GET /metrics` — metricas, solo si la integracion esta activa
- `GET /v1/observability/dashboard` — panel JSON minimo con resumen de consulta, workers y fuentes
- `GET /v1/observability/alerts` — alertas operativas derivadas del estado actual sin depender de revision manual
- `GET /v1/sources/manifest` — manifiesto vivo de fuentes con owner, trust tier, cadencia y deteccion de cambios
- `GET /v1/sources/freshness` — ledger de freshness por fuente con `snapshot_at`, `snapshot_version`, `previous_snapshot_at` y senal `changed_since_previous`

## Busqueda y legislacion

- `GET /v1/consulta` — consulta fiscal agregada con resultados, relevancia, confianza y score de faithfulness
- `GET /v1/connectivity/articulos/{codigo_norma}/{numero}` — conectividad cross-source derivada para un articulo: modelos, doctrina y obligaciones enlazadas
- `GET /v1/connectivity/documentos/{referencia}` — conectividad derivada para un documento: articulos y obligaciones enlazadas
- `GET /v1/connectivity/obligaciones/{codigo}` — conectividad derivada para una obligacion: documentos y articulos enlazados
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
- usa `connectivity/articulos` cuando quieras explorar relaciones cross-source explicitamente en vez de inferirlas desde varios endpoints sueltos
- usa `connectivity/documentos` o `connectivity/obligaciones` cuando el nodo raiz de tu analisis no sea el articulo sino el documento doctrinal o la obligacion operativa
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
- `GET /v1/modelos/{codigo}` — detalle completo del modelo
- `GET /v1/modelos/{codigo}/articulos`
- `GET /v1/modelos/{codigo}/casillas`
- `GET /v1/modelos/{codigo}/claves`
- `GET /v1/modelos/{codigo}/instrucciones`
- `GET /v1/modelos/{codigo}/normativa`
- `GET /v1/modelos/{codigo}/artefactos`
- `GET /v1/modelos/{codigo}/resumen-operativo`
- `GET /v1/modelos/{codigo}/campana-operativa`
- `GET /v1/modelos/{codigo}/fuentes-oficiales`

Uso recomendado:

- usa `/{codigo}` cuando quieras una vista completa
- usa endpoints especializados cuando necesites payload mas pequeno o UI mas focalizada

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

- `GET /v1/bdns`
- `GET /v1/bdns/{referencia}`
- `GET /v1/borme`
- `GET /v1/borme/{referencia}`
- `GET /v1/cnmv`
- `GET /v1/cnmv/{referencia}`
- `GET /v1/sepblac`
- `GET /v1/sepblac/{referencia}`
- `GET /v1/cendoj`
- `GET /v1/cendoj/{referencia}`
- `GET /v1/eurlex`
- `GET /v1/eurlex/{referencia}`
- `GET /v1/bde`
- `GET /v1/bde/{referencia}`
- `GET /v1/aepd`
- `GET /v1/aepd/{referencia}`

## Gobernanza AI (AI Act compliance)

- `GET /v1/ai/risk/register` — registro de riesgos AI activos
- `POST /v1/ai/risk/report` — reporte de incidente de riesgo
- `GET /v1/ai/audit-log` — auditoria de decisiones AI (filtrado por fecha/componente)
- `GET /v1/ai/audit-log/{request_id}` — log completo de una peticion
- `GET /v1/ai/fairness-report` — evaluacion de sesgo (geografico, temporal, fuente)
- `GET /v1/ai/models` — registry de modelos IA registrados y versions
- `GET /v1/data/lineage` — lineage y calidad de datos por tabla/campo
- `GET /v1/data/quality` — score de calidad por tabla
- `GET /v1/data/catalog` — catalogo completo de fuentes y tablas trazadas
- `POST /v1/gdpr/solicitud` — creacion de solicitud ARCO (acceso, rectificacion, supresion, etc.)
- `GET /v1/gdpr/dpia` — resumen de evaluacion de impacto (DPIA)
- `GET /v1/human-review/pending` — revisiones humanas pendientes
- `POST /v1/human-review/{id}/decide` — aprobar/rechazar/modificar revision
- `GET /v1/human-review/history` — historial de revisiones humanas
- `GET /v1/xai/explain` — explicabilidad de resultados de busqueda

Uso recomendado:

- `fairness-report` para auditorias de sesgo y cumplimiento AI Act
- `risk/register` y `risk/report` para gestion continua de riesgos
- `audit-log` para trazabilidad de decisiones AI ante reguladores
- `gdpr/solicitud` para ejercer derechos ARCO de titulares de datos
- `human-review` para flujos de supervision humana en consultas criticas
- `xai/explain` para entender por que un chunk es relevante en los resultados
- `ai/models` para verificar version y configuracion del modelo en uso
- `data/lineage` y `data/quality` para auditoria de origen y calidad de datos

## Referencias

- `../../apps/api/main.py`
- `../../apps/api/routers/`
- `../openapi-gpt.json`
