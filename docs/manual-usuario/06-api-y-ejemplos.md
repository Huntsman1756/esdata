# API y ejemplos

## Principio general

La `API` HTTP es la forma mas estable de integrar `esdata` en otras aplicaciones, automatizaciones o backends.

La documentacion de contrato debe consultarse siempre en OpenAPI, pero este capitulo da ejemplos practicos de uso.

La integracion MCP se documenta aparte en `07-mcp-y-clientes.md`. Este capitulo se limita a `REST/OpenAPI`.

## Endpoints base utiles

- `GET /health`
- `GET /status`
- `GET /openapi.json`

## Superficies de busqueda

| Endpoint | Que busca | Ejemplo |
|---|---|---|
| `/v1/consulta` | Legislacion + modelos, con grounding y abstencion | `?q=tipo+reducido+IVA` |
| `/v1/buscar` | Legislacion indexada unicamente | `?q=prescripcion+LGT` |
| `/v1/modelos/` | Modelos tributarios (303, 349, 100...) | `/v1/modelos/303` |

`/v1/buscar?q=modelo+303` devuelve vacio por diseno: los modelos tributarios no son legislacion y se sirven desde `/v1/modelos/`.

## Ejemplos rapidos

Consulta fiscal agregada:

```bash
curl -G -s http://127.0.0.1:8000/v1/consulta --data-urlencode "q=tipo reducido iva"
```

La respuesta de `GET /v1/consulta` expone ahora:

- `relevancia` con `nivel`, `score` y terminos encontrados/faltantes
- `confianza` con `nivel`, `fuentes`, `faithfulness_score`, `faithfulness_label` y `review_required`
- `resultados[*].evidencia` cuando existe grounding trazable por resultado
- `cited_chunks` con los anclajes priorizados por el reranker, incluyendo `chunk_id`, `source_document`, `rerank_score` y `excerpt`
- cabeceras `X-Generated-By` y `X-AI-Disclaimer` para marcar que la salida esta asistida por IA

### Regla operativa para uso interno

- `GET /v1/consulta` no debe tratarse como fuente de verdad por si sola
- si la evidencia es insuficiente, el endpoint puede abstenerse y devolver `resultados=[]`
- cuando `confianza.review_required=true`, la salida debe revisarse contra la fuente oficial antes de tomar decisiones fiscales o regulatorias
- cada consulta queda asociada a `X-Request-ID` para reconstruccion posterior en la auditoria durable

Health:

```bash
curl -s http://127.0.0.1:8000/health
```

Estado agregado de workers:

```bash
curl -s -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/status
```

Panel minimo de observabilidad:

```bash
curl -s http://127.0.0.1:8000/v1/observability/dashboard
```

Alertas operativas derivadas:

```bash
curl -s http://127.0.0.1:8000/v1/observability/alerts
```

Ledger de freshness por fuente:

```bash
curl -s http://127.0.0.1:8000/v1/sources/freshness
```

La respuesta de `GET /v1/sources/freshness` expone ahora `snapshot_at`, `snapshot_version`, `previous_snapshot_at` y `changed_since_previous` por fuente, ademas del estado de freshness calculado.

Disponibilidad explicita de dominios/tablas:

```bash
curl -s "http://127.0.0.1:8000/v1/domain-availability?only_empty=true"
```

La respuesta separa tablas no consultables directamente en estados seguros:
`workflow_empty`, `allowed_empty` y `configured_but_unavailable`. `only_empty=true`
incluye tambien tablas configuradas que no se pueden contar en la instancia
actual (`row_count=null`), porque tampoco son seguras para responder. Un agente
no debe inventar respuesta si el dominio requerido aparece bloqueado.

```bash
curl -s http://127.0.0.1:8000/v1/domain-availability/wallet_custodian
```

Nota: los endpoints `/v1/connectivity/*` existen como router en el repositorio,
pero no estan montados en la app runtime v1.0.

Busqueda general de legislacion:

```bash
curl -G -s http://127.0.0.1:8000/v1/buscar --data-urlencode "q=iva intracomunitario"
```

Si la necesidad es recuperar un modelo AEAT concreto, usa `GET /v1/modelos/{codigo}` o `GET /v1/consulta` en lugar de `GET /v1/buscar`.

Busqueda de legislacion:

```bash
curl -G -s http://127.0.0.1:8000/v1/legislacion/buscar --data-urlencode "q=retenciones no residente"
```

Detalle de una norma:

```bash
curl -s http://127.0.0.1:8000/v1/legislacion/LIVA
```

Detalle de un articulo:

```bash
curl -s http://127.0.0.1:8000/v1/legislacion/LIVA/articulos/104
```

## Modelos AEAT

Listar modelos:

```bash
curl -s http://127.0.0.1:8000/v1/modelos
```

Detalle completo de un modelo:

```bash
curl -G -s http://127.0.0.1:8000/v1/modelos/303 \
  --data-urlencode "casillas_limit=200" \
  --data-urlencode "casillas_offset=0"
```

Detalle por campana:

```bash
curl -G -s http://127.0.0.1:8000/v1/modelos/303 --data-urlencode "campana=2025"
```

Casillas de un modelo:

```bash
curl -G -s http://127.0.0.1:8000/v1/modelos/303/casillas \
  --data-urlencode "campana=2025" \
  --data-urlencode "limit=50" \
  --data-urlencode "offset=0"
```

Para modelos con muchas casillas, como el modelo 100, no pedir el listado completo en una sola respuesta. Usar `limit`, `offset`, `q`, `tipo_casilla` o `pagina`, y continuar solo si la respuesta trae `has_more=true`.
`GET /v1/modelos/{codigo}` tambien pagina las casillas embebidas mediante
`casillas_limit`/`casillas_offset` y devuelve `casillas_total`,
`casillas_has_more` y `casillas_next_offset`.

Vista operativa multi-modelo:

```bash
curl -G -s http://127.0.0.1:8000/v1/modelos/campanas-operativas --data-urlencode "codigos=124,216,296" --data-urlencode "campana=2025"
```

## Convenios DTA y retenciones internacionales

Listar convenios DTA:

```bash
curl -G -s http://127.0.0.1:8000/v1/internacional/convenios --data-urlencode "pais_a=US" --data-urlencode "pais_b=ES"
```

Detalle de un convenio:

```bash
curl -s http://127.0.0.1:8000/v1/internacional/convenios/ES_US_DTA
```

Listar reglas de retencion:

```bash
curl -G -s http://127.0.0.1:8000/v1/internacional/convenios/retenciones --data-urlencode "tipo_renta=dividends"
```

Calcular retencion aplicable:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/internacional/convenios/retencion \
  -H "Content-Type: application/json" \
  -d '{"pais_residencia":"US","tipo_renta":"dividends"}'
```

Reglas practicas:

- estos endpoints exponen convenios DTA y reglas de retencion ya cargados en la instancia; no implican cobertura exhaustiva de todos los paises
- el calculo de `retencion` cruza la regla de withholding por tipo de renta con un convenio DTA vigente si existe para la pareja de paises consultada
- en fixtures y compatibilidad legacy pueden coexistir codigos como `DTA_US_ES` y `ES_US_DTA`; usa en ejemplos solo los codigos verificados por tests o por la instancia objetivo

## Obligaciones regulatorias

Listar obligaciones:

```bash
curl -s http://127.0.0.1:8000/v1/obligaciones
```

Filtrar obligaciones operativas con sancion:

```bash
curl -G -s http://127.0.0.1:8000/v1/obligaciones/operativas --data-urlencode "ambito=mercado_valores" --data-urlencode "frecuencia=trimestral" --data-urlencode "con_sancion=true"
```

Obligaciones aplicables para perfil base:

```bash
curl -G -s http://127.0.0.1:8000/v1/obligaciones/aplicables --data-urlencode "tipo_entidad=sociedad_valores" --data-urlencode "reporting_reservado=true" --data-urlencode "aml_cft_reforzado=true"
```

Este endpoint devuelve `total`, `limit`, `offset`, `has_more` y `next_offset`.
Para MCP/Actions, usar `limite` y `offset` en vez de pedir todo el conjunto de
obligaciones en una sola respuesta. Si devuelve `total=0`, debe venir con
`status=evidence_limited`, `verified=false` y `confidence.review_required=true`;
eso no significa que no existan obligaciones, sino que ESData no tiene evidencia
aplicable verificada para ese perfil.

Detalle de una obligacion:

```bash
curl -s http://127.0.0.1:8000/v1/obligaciones/CNMV-IR-RESERVADA
```

## Compliance y cambios

Workflow de compliance:

```bash
curl -s http://127.0.0.1:8000/v1/compliance/workflow
```

Cambios regulatorios:

```bash
curl -G -s http://127.0.0.1:8000/v1/cambios --data-urlencode "fuente=cnmv" --data-urlencode "prioridad=alta"
```

## Entidades y screening

Buscar entidad por LEI:

```bash
curl -s http://127.0.0.1:8000/v1/entidades/lei/529900T8BM49AURSDO55
```

Busqueda de entidades:

```bash
curl -G -s http://127.0.0.1:8000/v1/entidades/buscar --data-urlencode "q=Banco Santander"
```

Chequeo de screening:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/screening/ \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Banco Santander","tipo_entidad":"organization"}'
```

## PGC

Buscar cuentas PGC:

```bash
curl -G -s http://127.0.0.1:8000/v1/pgc/buscar --data-urlencode "q=clientes"
```

Filtrar cuentas PGC:

```bash
curl -G -s http://127.0.0.1:8000/v1/pgc/cuentas --data-urlencode "grupo=43"
```

## Recomendaciones practicas

- para integraciones productivas, basarse en `openapi.json` y no solo en este manual
- cuando el endpoint tenga query params de campana, pasarlos explicitamente si necesitas reproducibilidad
- para automatizaciones, usar `health` y `status` antes de asumir que el stack esta operativo

## Referencias

- `../openapi-gpt.json`
- `../openapi-gpt-3.0.json`
- `../../apps/api/main.py`
