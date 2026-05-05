# Arquitectura de esdata

## Resumen

`esdata` es una plataforma backend-first para ingesta, normalizacion y consulta fiscal-regulatoria con trazabilidad a fuente oficial. Esta referencia se organiza en dominios modulares principales: backend API, UI interna, pipelines de ingestion, tooling operativo fuera del runtime e infraestructura de despliegue.

- `apps/api/` — backend FastAPI y puntos de entrada de integracion
- `apps/web/` — UI interna para consulta y operacion
- `apps/workers/` — pipelines de ingestion y normalizacion por fuente
- `scripts/` — tooling, mantenimiento y tareas operativas fuera del runtime
- `infra/` — despliegue, bootstrap SQL y configuracion operativa reproducible

## Mapa modular

### `apps/api`

- Backend FastAPI para consulta, orquestacion y exposicion de interfaces de integracion.
- Centraliza routers, servicios, validacion, middleware y contratos de API.

### `apps/web`

- UI interna para consumir capacidades del backend.
- No es la capa de negocio ni la fuente de verdad de datos.

### `apps/workers`

- Pipelines de ingestion, parsing y normalizacion por fuente.
- Alimentan el almacenamiento y las capas de retrieval del sistema.

### `scripts`

- Tooling y mantenimiento fuera del runtime de producto.
- Agrupa seeds, backfills, evaluacion y utilidades operativas.

### `infra/`

- Despliegue y orquestacion de runtime, bootstrap SQL, observabilidad y configuracion perimetral como concerns de infraestructura reproducible.
- Reune la base de infraestructura sobre la que corre el sistema.

## Flujo de datos

### Ingestion

```text
fuente oficial -> worker -> normalizacion -> PostgreSQL
```

### Consulta

```text
cliente -> superficie de integracion -> apps/api -> services/routers -> PostgreSQL -> respuesta trazable
```

## Superficies de integracion activas

El backend de `esdata` expone tres superficies de integracion distintas.
Esta seccion enumera las superficies de integracion del backend; la UI interna es un cliente humano separado sobre ese backend.

### REST/OpenAPI `[IMPLEMENTED]`

- Superficie HTTP mas estable para integraciones backend y aplicacion.
- Su familia de contratos se ancla en el esquema OpenAPI expuesto por la API en `/openapi.json`; las especificaciones derivadas del repo, como `docs/openapi-gpt*.json`, son proyecciones de esa misma superficie para integraciones concretas, no una superficie backend separada.

### HTTP MCP `[IMPLEMENTED]`

- Superficie MCP remota montada sobre HTTP en `/mcp`.
- Su catalogo HTTP se define en `apps/api/mcp_catalog.py` bajo `HTTP_MCP_OPERATIONS`.

### stdio MCP `[IMPLEMENTED]`

- Superficie MCP local definida en `apps/api/mcp_stdio.py`.
- Expone un catalogo distinto del catalogo HTTP.

HTTP MCP y stdio MCP no comparten catalogo ni semantica, aunque ambas superficies se apoyan en capacidades del backend.

## Capas arquitectonicas de referencia

### Fuente de verdad transaccional

- `PostgreSQL` es el sistema de registro para documentos, entidades, metadatos y evidencia derivada.
- La persistencia durable de auditoria y lineage se ancla en almacenamiento transaccional.

### Ingestion y freshness

- Cada fuente deja rastro durable de origen, cambios y versionado de procesamiento.
- Esta capa soporta reprocesado, reindexado y reconstruccion historica de respuestas.

### Conectividad derivada

- Una capa derivada relaciona normas, doctrina, obligaciones, entidades y evidencia.
- Esa capa complementa al sistema transaccional y habilita traversal cross-source.

### Retrieval

- El retrieval combina senales lexicas y semanticas con reranking y seleccion final de evidencia citable.
- Toda respuesta factual queda trazada a evidencia recuperada y a su revision de origen.

### Inferencia con grounding

- La inferencia opera sobre retrieval y no convierte el modelo en fuente de verdad.
- Cada afirmacion factual se valida contra evidencia recuperada, con abstencion cuando la base es insuficiente.

### Auditoria

- Cada consulta relevante debe dejar evidencia durable de entrada, contexto de ejecucion, fuentes usadas y salida emitida.
- La auditoria permite reconstruir por que superficie respondio el sistema y con que respaldo documental.

### Observabilidad

- La observabilidad cubre ingestion, retrieval, inferencia y errores por componente.
- Esta capa soporta diagnostico operativo, control de calidad y seguimiento de fiabilidad.

## Jerarquia de confianza de informacion

1. fuente oficial primaria
2. fuente oficial secundaria o portal institucional derivado
3. curacion interna controlada
4. fixture local o corpus auxiliar
5. dato sintetico de test
6. sintesis LLM

Regla: una sintesis LLM no es fuente de verdad; solo puede derivarse de fuentes anteriores y debe citar sus anchors.

## Base de datos

- Motor principal: PostgreSQL 16.
- Migraciones oficiales: Alembic.

## Despliegue

- Modo de despliegue de referencia: Docker Compose.
