# Arquitectura de esdata

## Resumen

esdata es un sistema de ingesta, almacenamiento y consulta de legislacion fiscal espanola consolidada, doctrina interpretativa y modelos tributarios AEAT. Proporciona una API REST publica y un frontend web, con workers de ingestion asincrona que alimentan una base de datos PostgreSQL.

## Componentes

### 1. API (apps/api)

Servidor FastAPI que expone endpoints REST para consulta publica.

- **Framework**: FastAPI 0.116.1 con Uvicorn
- **ORM**: SQLAlchemy 2.0.43 con psycopg3
- **Version**: 0.1.6
- **Puerto**: 8000 (expuesto como 8001 en local)
- **Lifespan**: Carga el modelo de embeddings al iniciar para busqueda hibrida

**Routers registrados**:

| Router | Ruta base | Descripcion |
|--------|-----------|-------------|
| `status` | `/v1/status` | Healthcheck y version |
| `buscar` | `/v1/legislacion/buscar` | Busqueda fulltext de legislacion |
| `buscar` | `/v1/legislacion/buscar/hybrid` | Busqueda hibrida (fulltext + vector) |
| `legislacion` | `/v1/legislacion/*` | CRUD de normas, articulos, busqueda |
| `materias` | `/v1/materias/*` | Listado y detalle de materias |
| `doctrina` | `/v1/doctrina/*` | Busqueda y detalle de doctrina (DGT, TEAC) |
| `bdns` | `/v1/bdns/*` | Base de datos de subvenciones |
| `borme` | `/v1/borme/*` | Boletin oficial del registro mercantil |
| `cnmv` | `/v1/cnmv/*` | Comision nacional del mercado de valores |
| `sepblac` | `/v1/sepblac/*` | Servicio de vigilancia de blanqueo de capitales |
| `obligaciones` | `/v1/obligaciones/*` | Obligaciones regulatorias tributarias |
| `empresas` | `/v1/empresas/*` | Empresas detectadas en documentos |
| `modelos` | `/v1/modelos/*` | Modelos tributarios AEAT (303, 216, etc.) |
| `consulta` | `/v1/consulta` | Consulta fiscal inteligente (agrega multiples fuentes) |
| `chunks` | `/v1/chunks/*` | Acceso a chunks de legislacion |
| `cendoj` | `/v1/cendoj/*` | Centro de documentacion del Consejo de Estado |
| `eurlex` | `/v1/eurlex/*` | Legislacion de la Union Europea |
| `bde` | `/v1/bde/*` | Banco de Espana |
| `aepd` | `/v1/aepd/*` | Agencia espanola de proteccion de datos |

**Servicios principales**:

- `search.py`: Busqueda fulltext en PostgreSQL con `ts_rank`, `websearch_to_tsquery`, `tsvector`. Incluye chunks, boost, fallback SQLite y deteccion automatica de normas en query.
- `semantic_search.py`: Busqueda hibrida con RRF (Reciprocal Rank Fusion). Combina fulltext y embeddings vectoriales con pesos configurables.
- **Schemas**: Pydantic models para todas las respuestas de la API (677 lineas, 40+ modelos de respuesta).

### 2. Workers (apps/workers)

Procesos asincronos de ingestion que descargan, parsean y almacenan datos de fuentes externas.

**Workers activos**:

| Worker | Fuente | Frecuencia | Descripcion |
|--------|--------|------------|-------------|
| `boe.py` | BOE | 1 hora (configurable) | Legislacion consolidada (15 normas tributarias) |
| `modelos.py` | AEAT | 24 horas | Modelos tributarios (303, 100, 216, etc.) |
| `bdns.py` | Infosubvenciones | 7 dias | Convocatorias de subvenciones |
| `borme.py` | BOE BORME | 7 dias | Actos mercantiles |
| `cnmv.py` | CNMV | 7 dias | Documentos regulatorios |
| `sepblac.py` | SEPBLAC | 7 dias | Publicaciones anticorrupcion |
| `dgt.py` | DGT | Segun config | Consultas vinculantes |
| `teac.py` | TEAC | Segun config | Resoluciones del Tribunal Economico-Administrativo Central |
| `embeddings.py` | Local | On-demand | Generacion de embeddings con sentence-transformers |

**Worker BOE (principal)**:
- Descarga XML del BOE API (`/api/legislacion-consolidada`)
- Parsea articulos, versiones y metadatos
- Almacena en `articulo`, `version_articulo`, `norma`
- Clasifica normas por ambito (tributario, local, internacional, UE)
- Log de sincronizacion en `sync_log` con duracion automatica

**Worker Embeddings**:
- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (1536-dim, CPU-friendly)
- Funciones: `embed_single(text)`, `embed_texts(texts)` con batching
- Genera embeddings para `version_articulo`, `documento_fragmento`, `documento_interpretativo`

**Runtime comun**:
- `runtime.py`: Utilidades compartidas (parseo de URL DB, intervalos de sincronizacion)
- Todos los workers heredan patron de `log_sync()` con `started_at`/`finished_at`

### 3. Web (apps/web)

Frontend Next.js 15 para consulta publica.

- **Framework**: Next.js 15
- **Puerto**: 3000 (expuesto como 3005 en local)
- **API base**: `ESDATA_API_BASE_URL` (apunta a `http://api:8000` en Docker)

## Base de datos

### Motor

PostgreSQL 16 con extension pgvector.

- **Imagen**: `pgvector/pgvector:pg16`
- **DB**: `esdata`
- **Usuario**: `esdata`

### Tablas principales

| Tabla | Descripcion |
|-------|-------------|
| `norma` | Leyes y normativas (LIVA, LIRPF, LIS, etc.) |
| `articulo` | Articulos de leyes |
| `version_articulo` | Versiones historicas con texto vigente |
| `documento_seccion` | Secciones de documentos para chunking |
| `documento_fragmento` | Chunks de texto con `tsvector` y `vector(1536)` |
| `documento_interpretativo` | Doctrina, BORME, BDNS con embedding |
| `documento_articulo` | Relacion documento-articulo |
| `sync_log` | Historial de sincronizacion de workers |
| `articulo_norma` | Relacion articulo-norma |
| `materia` | Materias tematicas |
| `eval_run` | Historial de evaluaciones |
| `eval_query` | Resultados por query de evaluacion |

### Indices

- **Fulltext**: `tsvector` en `documento_fragmento.search_vector`
- **Vector**: HNSW en `documento_fragmento.embedding`, `version_articulo.embedding`, `documento_interpretativo.embedding` (m=16, ef_construction=64)
- **Critic**: `articulo(norma_id)`, `version_articulo(articulo_id)`, `documento_articulo(documento_id)`, `documento_fragmento(origen_tipo_id)`, `sync_log(worker, started_at)`

### Migraciones

- **Manual**: SQL en `infra/sql/` (init, fulltext, modelos, chunking, indexes, pgvector)
- **Alembic**: Migraciones en `alembic/versions/` (chunking, eval_history, indexes)

## Flujo de datos

### Ingestion BOE

```
BOE API (XML) -> worker-boe -> parse XML -> articulo/version_articulo/norma
  -> sync_log -> documento_fragmento (chunking) -> embedding (workers)
```

1. `worker-boe` llama a `BOE_API_BASE/datosabiertos/api/legislacion-consolidada`
2. Descarga XML con articulos y versiones de las 15 normas en `DEFAULT_NORMAS`
3. Parsea estructura XML: articulos, parrafos, textos, fechas de vigencia
4. Inserta/actualiza en `norma`, `articulo`, `version_articulo`
5. Clasifica norma con `NORMA_CLASSIFICATIONS` (tipo_documento, ambito)
6. Genera chunks en `documento_fragmento` (backfill via `scripts/backfill_chunks.py`)
7. Genera embeddings (backfill via `scripts/backfill_embeddings.py`)

### Consulta API

```
Request -> Router -> Service (search/semantic_search) -> PostgreSQL -> Response
```

1. Router recibe request (ej: `/v1/legislacion/buscar?q=IVA+retencion`)
2. `search_legislacion()` detecta norma automatica de la query ("IVA" -> "LIVA")
3. Construye tsquery con `websearch_to_tsquery('spanish', ...)`
4. Busca en `documento_fragmento` con `ts_rank`, boost por chunks
5. Fallback a `version_articulo` si `documento_fragmento` esta vacio
6. Fallback a SQLite si PostgreSQL no disponible
7. Respuesta con `SearchResult` incluyendo `source_url`, `fuente_norma`, `fragmento`, `confianza`

### Busqueda hibrida

```
Request -> Router -> semantic_search.hybrid_search -> RRF merge -> Response
```

1. Mismo inicio que busqueda fulltext (tsquery)
2. Paralelamente: busqueda vectorial por similitud cosine en `embedding`
3. Fusiona resultados con RRF (Reciprocal Rank Fusion): `score = w_ft * rank_ft/(k+rank_ft) + w_vec * rank_vec/(k+rank_vec)`, k=60
4. `hybrid_weight=0.3` es optimo: 100% recall con mezcla fulltext+vector
5. Response incluye `search_mode`, `weights`, `rrf_score`, `rrf_sources`

### Consulta fiscal inteligente

```
Request `/v1/consulta` -> Router consulta -> Multiples servicios -> Resultados agregados
```

1. Recibe query en lenguaje natural
2. Busca en legislacion, doctrina, modelos AEAT, obligaciones
3. Agrega resultados con `ConsultaResultado` (tipo, codigo, texto, evidencia)
4. Calcula relevancia y confianza
5. Respuesta con `ConsultaFiscalResponse` (modelos, resultados, relevancia, confianza)

## Patrones de seguridad

- Sin autenticacion en endpoints publicos
- Sin secretos expuestos en frontend (no `NEXT_PUBLIC_*`)
- Validacion de input en toda mutacion
- Rate limiting en endpoints publicos
- Docker: usuario `app` non-root, sin secretos en capas de imagen
- PostgreSQL: indexes criticos para evitar full table scans

## Dependencias externas

| Fuente | URL | Uso |
|--------|-----|-----|
| BOE | `boe.es/datosabiertos/api/` | Legislacion consolidada |
| AEAT | Sede electronica | Modelos tributarios |
| DGT | `sede.organcp.es` | Consultas vinculantes |
| TEAC | `hacienda.es` | Resoluciones economico-administrativas |
| CNMV | `cnmv.es` | Documentos regulatorios |
| SEPBLAC | `sepblac.es` | Publicaciones anticorrupcion |
| BORME | `boe.es/borme` | Actos mercantiles |
| BDNS | `infosubvenciones.es` | Convocatorias subvenciones |
| EURLEX | `eur-lex.europa.eu` | Legislacion UE |
| PLACE | `place.boe.es` | Datos administrativos (post-v2) |
| HuggingFace | `sentence-transformers` | Modelo de embeddings |

## Versiones

- **Python**: 3.12
- **FastAPI**: 0.116.1
- **SQLAlchemy**: 2.0.43
- **psycopg**: 3.2.9 (binary)
- **Alembic**: 1.16.4
- **sentence-transformers**: 4.1.0
- **PostgreSQL**: 16 (pgvector)
- **Redis**: 7 (alpine)
- **Next.js**: 15
