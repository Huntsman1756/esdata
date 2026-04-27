# Arquitectura de esdata

## Resumen

`esdata` es una plataforma backend-first para ingesta, normalizacion y consulta fiscal-regulatoria con trazabilidad a fuente oficial.

La arquitectura operativa actual se apoya en cuatro superficies claras:

- `apps/api/` — runtime FastAPI y superficies MCP/API
- `apps/web/` — UI interna y consumo web del backend
- `apps/workers/` — ingestion y pipelines por fuente
- `scripts/` — tooling no-runtime: seeds, backfills, ops, evaluacion y mantenimiento

## Principios de diseno

- backend-first: la logica de negocio vive en backend, no en frontend
- una sola fuente activa de estado: `docs/master-execution-roadmap.md`
- boundaries claros entre runtime y tooling
- cambios pequenos, verificables y reversibles
- documentacion viva separada de historicos

## Mapa modular

### API (`apps/api`)

Contiene solo runtime importable del backend.

Estructura principal:

- `main.py` — entrada FastAPI y montaje de routers
- `routers/` — endpoints HTTP por dominio
- `services/` — logica de consulta y orquestacion
- `middleware/` — seguridad, auth, rate limit, logging y metrics
- `banking/` — parsing y utilidades bancarias del dominio
- `schemas.py` — contratos Pydantic
- `db.py` — acceso SQLAlchemy
- `mcp_*` — superficies MCP/guardas del backend
- `tests/` — tests del API

Regla:

- seeds, scripts manuales, wrappers y verificaciones no viven aqui; viven en `scripts/`

### Workers (`apps/workers`)

Contiene runtime de ingestion y normalizacion por fuente.

Estructura actual:

- un modulo por fuente o pipeline principal
- `runtime.py` — utilidades compartidas
- `tests/` — tests del modulo

Regla:

- si algo es un comando manual o de mantenimiento, debe vivir en `scripts/`, no en `apps/workers/`

### Web (`apps/web`)

Contiene la UI interna y su consumo del backend.

Regla:

- no contiene logica de negocio ni acceso directo a DB

### Tooling (`scripts`)

Todo lo que no es runtime de producto vive aqui.

Subcarpetas activas:

- `dev/` — wrappers y pruebas manuales locales
- `data/` — seeds, backfills e ingestas manuales
- `eval/` — evaluacion y quality gates
- `ops/` — despliegue y utilidades operativas
- `maintenance/` — verificaciones y saneamiento

Regla:

- cada tarea operativa debe tener un nombre canonico unico; no mantener copias duplicadas con sufijos heredados como `_api` si hacen lo mismo
- `tests/` — tests de scripts no triviales

## Flujo de datos

### Ingestion

```text
fuente oficial -> worker -> normalizacion -> PostgreSQL
```

### Consulta

```text
cliente/API/MCP -> apps/api -> services/routers -> PostgreSQL -> respuesta trazable
```

## Estado real de la arquitectura actual

La arquitectura actual ya implementa una base util, pero no debe confundirse con una plataforma plenamente fiable de conocimiento conectado.

Capacidades reales hoy:

- [IMPLEMENTED] ingesta multi-fuente por workers especializados
- [IMPLEMENTED] almacenamiento principal en PostgreSQL
- [IMPLEMENTED] full-text search, chunking y busqueda vectorial/hibrida con reranker cross-encoder activo y grounding duro por claim
- [IMPLEMENTED] superficies API y MCP para consulta

Limitaciones estructurales vigentes:

- [PARTIAL] la conectividad cross-source global no esta modelada de forma explicita; hoy predomina el fan-out por tablas y fusion heuristica
- [PARTIAL] existen piezas de AI governance durables, pero la auditoria de consulta end-to-end sigue incompleta mientras `query_audit` no este cableado al runtime
- [IMPLEMENTED] la trazabilidad de retrieval devuelve `chunk_id`, `source_hash`, grounding por claim con `grounded` flag, y abstencion por evidencia insuficiente
- [PARTIAL] la observabilidad actual cubre salud HTTP, freshness y metricas basicas, pero no retrieval P95/P99, token count, coste ni error budget por componente

## Arquitectura objetivo post-auditoria

Estado de lectura:

- `[IMPLEMENTED]` = presente en runtime activo y verificable
- `[PARTIAL]` = presente solo en parte, sin cableado completo o sin control suficientemente fuerte
- `[TARGET]` = direccion deseada, no implementada aun

La direccion tecnica objetivo para `esdata` es:

```text
fuentes oficiales y locales controladas
-> ingestion workers
-> ledger de snapshots y cambios
-> chunking + embeddings versionados
-> PostgreSQL (fuente de verdad transaccional)
-> capa de conectividad derivada
-> retrieval hibrido + reranking
-> inferencia LLM con grounding estricto
-> validacion de salida + respuesta con citas exactas
-> audit logs + observabilidad + alertas
```

### Capas objetivo

#### 1. Fuente de verdad transaccional `[IMPLEMENTED]`

- `PostgreSQL` sigue siendo la fuente de verdad para datos ingestados, documentos, chunks, obligaciones, entidades y metadatos
- toda persistencia de auditoria y lineage debe vivir aqui o en almacenamiento durable equivalente

#### 2. Ledger de ingestion y freshness `[PARTIAL]`

Cada fuente debe producir registros durables de:

- URL o identificador origen
- timestamp de fetch
- `etag`, `last-modified` o `sha256` del payload
- resumen de delta
- version de chunking aplicada
- version del modelo de embeddings usada

Objetivo:

- permitir reindexado incremental y reconstruccion historica del estado de una respuesta

#### 3. Capa de conectividad derivada `[PARTIAL]`

`esdata` necesita una capa explicita para responder relaciones del tipo:

- que normas, doctrina, obligaciones y entidades se relacionan con X
- que fuentes contradicen o complementan una respuesta
- que documentos referencian o desarrollan un articulo concreto

Direccion recomendada:

- mantener `PostgreSQL` como sistema de registro
- poblar un grafo derivado local para exploracion y traversal cross-source
- preferir `Kuzu` como primera opcion por ser local, embebido y con menor complejidad operativa que una base separada mas pesada

Tipos de nodo minimos:

- `Fuente`
- `Norma`
- `Articulo`
- `Documento`
- `Chunk`
- `Obligacion`
- `Entidad`
- `IdentificadorEntidad`

Relaciones minimas:

- `EMITIDA_POR`
- `APLICA_A`
- `CITA_A`
- `DESARROLLA`
- `MENCIONA`
- `SUPERSEDE_A`
- `ORIGINA`
- `TIENE_CHUNK`

#### 4. Retrieval fiable `[PARTIAL]`

El retrieval objetivo no debe depender solo de una query SQL o de fusion heuristica.

Minimo esperado:

- full-text / BM25
- vector similarity
- reranker
- seleccion final de chunks citables

Cada resultado factual debe devolver al menos:

- `chunk_id`
- `source_url`
- `source_hash` o revision
- score de retrieval
- motivo de ranking

#### 5. Inference layer con grounding estricto `[IMPLEMENTED]`

Reglas implementadas:

- RAG solo en inferencia; el conocimiento no se "entrena" al cambiar el corpus
- grounding duro por claim: cada afirmacion factual se valida contra chunks con `rerank_score >= 0.4`
- abstencion automatica: si `grounding_status` es "partial" o "none", se filtran resultados no fundamentados
- chunks como input no confiable: deteccion de patrones de inyeccion adversarial (12+ patrones: DAN, ignore instructions, code blocks, base64, SQL injection, prompt leak)
- `grounding_summary` persistente en `query_audit_log` con status, scores y flags de inyeccion
- `grounded` flag por claim y `chunk_clean` flag por citation en respuesta
- revision humana via `human_review.py` con `ReviewStatus` enum y persistencia SQL dual (SQLite/PostgreSQL)
- faithfulness scoring con token overlap (citas strip, partial match tokens >= 5 chars)

#### 6. Validacion y auditoria `[IMPLEMENTED]`

Toda query relevante debe dejar evidencia durable de:

- quien consulto
- que se recupero
- que modelo/configuracion se uso
- que se respondio
- que score de faithfulness y confianza resulto
- si hubo revision humana

#### 7. Observabilidad minima real `[PARTIAL]`

Metricas minimas objetivo:

- RAM y VRAM por query cuando aplique
- latencia P95/P99 de retrieval
- error rate por componente
- token count por query
- lag y error rate de workers
- tendencia de faithfulness / confidence

## Jerarquia de confianza de informacion

Para evitar mezclar corpus heterogeneos sin criterio, toda fuente debe clasificarse en una jerarquia de confianza explicita:

1. fuente oficial primaria
2. fuente oficial secundaria o portal institucional derivado
3. curacion interna controlada
4. fixture local / corpus auxiliar
5. dato sintetico de test
6. sintesis LLM

Regla:

- una sintesis LLM nunca es fuente de verdad; solo puede derivarse de fuentes anteriores y debe citar sus anchors

## Regla de remediacion estructural

Mientras la remediacion estructural activa siga abierta en el roadmap maestro:

- no llamar "compliance fuerte" a controles en memoria
- no seguir ampliando superficie funcional sin cerrar primero la contencion operativa minima
- no documentar como "knowledge graph" tablas o joins parciales que no permitan traversal cross-source real

### Operacion y mantenimiento

```text
script manual -> scripts/* -> DB/API/infra segun caso
```

## Base de datos

- motor: PostgreSQL 16
- migraciones oficiales: Alembic
- SQL bootstrap y complementos: `infra/sql/`

## Despliegue

- despliegue activo: Docker Compose
- docs activas: `docs/deployment/overview.md`, `docs/deployment/server-installation.md`, `docs/deployment/rollback.md`
- plataformas antiguas: solo contexto historico en `docs/archive/`

## Documentacion y estado

- estado activo: `docs/master-execution-roadmap.md`
- manual vivo: `docs/manual-usuario/`
- runbooks: `docs/operations/`
- historicos: `docs/archive/`

## Regla de mantenimiento estructural

Si aparece un archivo nuevo, debe poder responderse rapidamente:

1. es runtime del producto?
2. es tooling/manual?
3. es documentacion activa?
4. es historico?

Si no encaja claramente en una de esas categorias, la estructura esta degradandose y debe corregirse.
