# Estructura del repositorio

## Arbol de directorios

```
esdata/
|-- apps/
|   |-- api/                          # API FastAPI publica
|   |   |-- main.py                   # Entry point FastAPI (lifespan, routers)
|   |   |-- schemas.py                # Pydantic models (677 lineas, 40+ modelos)
|   |   |-- db.py                     # Engine SQLAlchemy, db_session
|   |   |-- requirements.txt          # Dependencias API
|   |   |-- Dockerfile                # Imagen Docker API (python:3.12-slim)
|   |   |-- mcp_server.py             # MCP server mounting
|   |   |-- routers/                  # Endpoints REST
|   |   |   |-- status.py             # Healthcheck
|   |   |   |-- buscar.py             # /v1/legislacion/buscar + hybrid
|   |   |   |-- legislacion.py        # /v1/legislacion/*
|   |   |   |-- materias.py           # /v1/materias/*
|   |   |   |-- doctrina.py           # /v1/doctrina/*
|   |   |   |-- bdns.py               # /v1/bdns/*
|   |   |   |-- borme.py              # /v1/borme/*
|   |   |   |-- cnmv.py               # /v1/cnmv/*
|   |   |   |-- sepblac.py            # /v1/sepblac/*
|   |   |   |-- obligaciones.py       # /v1/obligaciones/*
|   |   |   |-- empresas.py           # /v1/empresas/*
|   |   |   |-- modelos.py            # /v1/modelos/*
|   |   |   |-- consulta.py           # /v1/consulta
|   |   |   |-- chunks.py             # /v1/chunks/*
|   |   |   |-- cendoj.py             # /v1/cendoj/*
|   |   |   |-- eurlex.py             # /v1/eurlex/*
|   |   |   |-- bde.py                # /v1/bde/*
|   |   |   |-- aepd.py               # /v1/aepd/*
|   |   |-- services/                 # Logica de negocio
|   |   |   |-- search.py             # Busqueda fulltext (481 lineas)
|   |   |   |-- semantic_search.py    # Busqueda hibrida RRF
|   |   |-- tests/                    # Tests de la API
|   |       |-- conftest.py           # Fixtures pytest
|   |       |-- test_*.py             # Tests de endpoints
|   |-- workers/                      # Workers de ingestion
|   |   |-- runtime.py                # Utilidades compartidas (DB URL, intervalos)
|   |   |-- requirements.txt          # Dependencias workers
|   |   |-- Dockerfile                # Imagen Docker workers
|   |   |-- boe.py                    # Worker BOE (legislacion consolidada)
|   |   |-- modelos.py                # Worker modelos AEAT
|   |   |-- bdns.py                   # Worker BDNS (subvenciones)
|   |   |-- borme.py                  # Worker BORME
|   |   |-- cnmv.py                   # Worker CNMV
|   |   |-- sepblac.py                # Worker SEPBLAC
|   |   |-- dgt.py                    # Worker DGT (consultas vinculantes)
|   |   |-- teac.py                   # Worker TEAC
|   |   |-- aepd.py                   # Worker AEPD
|   |   |-- bde.py                    # Worker BDE
|   |   |-- cendoj.py                 # Worker CENDOJ
|   |   |-- eurlex.py                 # Worker EURLEX
|   |   |-- embeddings.py             # Generacion de embeddings
|   |   |-- modelos_support.py        # Soporte modelos AEAT
|   |   |-- tests/                    # Tests de workers
|   |-- web/                          # Frontend Next.js 15
|       |-- Dockerfile                # Imagen Docker web
|-- infra/
|   |-- sql/                          # Schema y migraciones SQL
|       |-- init.sql                  # Creacion de tablas base
|       |-- 000_docker_init.sql       # Init especifico para Docker
|       |-- 002_fulltext_search.sql   # Configuracion fulltext (tsvector, tsquery)
|       |-- 003_modelos_aeat.sql      # Tablas de modelos AEAT
|       |-- 004_modelos_v2.sql        # Schema modelos v2
|       |-- 004_norma_classification.sql # Clasificacion de normas
|       |-- 005_indexes.sql           # Indices criticos de rendimiento
|       |-- 006_pgvector.sql          # Extension pgvector + embeddings
|-- alembic/                          # Migraciones Alembic
|   |-- versions/                     # Migraciones individuales
|       |-- 20260424_0005_chunking_schema.py  # Tablas chunking
|       |-- 20260425_0006_eval_history.py      # Tablas evaluacion
|       |-- 20260425_0007_critical_indexes.py  # Indices criticos
|-- scripts/                          # Scripts de operacion
|   |-- golden_queries.json           # Dataset 52 queries para evaluacion
|   |-- eval_phase3.py                # Evaluador automatico
|   |-- test_eval_phase3.py           # Tests unitarios del evaluador (47 tests)
|   |-- baseline.json                 # Baseline score 0.8764
|   |-- backfill_chunks.py            # Backfill de chunks
|   |-- backfill_embeddings.py        # Backfill de embeddings
|   |-- benchmark_hybrid.py           # Benchmark de hybrid_weight
|   |-- telemetry/                    # Datos de telemetria
|       |-- eval_failures.jsonl       # Fallos de evaluacion
|   |-- eval_results/                 # Resultados de evaluacion
|       |-- eval_YYYYMMDD_HHMMSS.json
|-- docs/                             # Documentacion
|   |-- architecture.md               # Arquitectura del sistema
|   |-- repository-structure.md       # Este archivo
|   |-- environment-variables.md      # Variables de entorno
|   |-- infrastructure-handoff.md     # Handoff de infraestructura
|   |-- professionalization-roadmap.md # Roadmap de profesionalizacion
|   |-- next-session-handoff-2026-04-25.md # Handoff de sesiones
|   |-- plan-fase2-chunking.md        # Plan Fase 2 chunking
|   |-- openapi-gpt-minimal-modelos.json # OpenAPI para GPT Actions
|-- infra/deploy/                     # Despliegue de produccion
|   |-- docker-compose.prod.yml       # Docker Compose produccion
|   |-- server-setup.sh               # Script de setup del servidor
|   |-- deploy.sh                     # Script de despliegue
|-- .github/workflows/                # CI/CD
|   |-- ci.yml                        # Pipeline CI (tests + eval-gate)
|-- docker-compose.yml                # Docker Compose desarrollo
|-- Makefile                          # Comandos operativos (make test, make api, make eval)
|-- alembic.ini                       # Configuracion Alembic
|-- .env.example                      # Variables de entorno de ejemplo
|-- .env                              # Variables de entorno locales (no commit)
|-- .gitignore                        # Git ignore
|-- README.md                         # README principal
|-- railway.toml                      # DEPRECATED - Railway (no usar)
|-- DEPLOY_CHECKLIST.md               # HISTORICO - Checklist de despliegue
|-- STRUCTURE.md                      # Estructura del repo (referencia rapida)
```

## Responsabilidades por modulo

### apps/api

- **main.py**: Creacion de app FastAPI, montaje de routers, lifespan (carga de embeddings), endpoints internos (/privacy, /gpt-actions)
- **schemas.py**: Todos los modelos Pydantic de respuesta. 40+ modelos organizados por dominio (legislacion, doctrina, modelos AEAT, BDNS, BORME, CNMV, SEPBLAC, empresas, obligaciones, chunks)
- **db.py**: Engine SQLAlchemy, session factory, `db_session()` context manager
- **routers/**: 19 routers REST, cada uno con sus endpoints GET/POST
- **services/**: Logica de busqueda (fulltext + hibrida RRF), logica de negocio

### apps/workers

- **runtime.py**: `get_database_url()`, `get_interval_seconds()`, utilidades comunes
- **boe.py**: Worker principal. 1164 lineas. Ingesta BOE, parsing XML, clasificacion de normas, sync_log
- **modelos.py**: Ingesta modelos AEAT (303, 100, 216, etc.)
- **embeddings.py**: Generacion de embeddings con sentence-transformers
- **bdns.py**, **borme.py**, **cnmv.py**, **sepblac.py**, **dgt.py**, **teac.py**, **aepd.py**, **bde.py**, **cendoj.py**, **eurlex.py**: Workers de fuentes especificas

### infra/

- **sql/**: Schema de base de datos. Archivos se cargan en `/docker-entrypoint-initdb.d/` en orden numerico
- **deploy/**: Despliegue de produccion. Docker Compose + scripts de deploy

### scripts/

- **eval_phase3.py**: Evaluador automatico con golden dataset, benchmarks, quality gate
- **golden_queries.json**: 52 queries de evaluacion en 8 dominios
- **baseline.json**: Score baseline 0.8764
- **backfill_chunks.py**: Genera chunks en `documento_fragmento`
- **backfill_embeddings.py**: Genera embeddings en columnas vector(1536)

## Convenciones de nombres

- **Routers**: `apps/api/routers/{nombre}.py` -> `/{nombre}` en URL
- **Workers**: `apps/workers/{fuente}.py` -> `worker-{fuente}` en docker-compose
- **Migraciones**: `YYYYMMDD_NNNN_descripcion.py` en `alembic/versions/`
- **SQL**: `NNN_nombre.sql` en `infra/sql/` (orden numerico de carga)
- **Resultados eval**: `eval_YYYYMMDD_HHMMSS.json` en `scripts/eval_results/`
- **Telemetria**: `eval_failures.jsonl` en `scripts/telemetry/`

## Dependencias por servicio

### API (apps/api/requirements.txt)
- fastapi 0.116.1
- uvicorn[standard] 0.35.0
- sqlalchemy 2.0.43
- psycopg[binary] 3.2.9
- alembic 1.16.4
- pytest 9.0.3
- pytest-asyncio 1.3.0
- httpx 0.28.1
- fastapi-mcp 0.4.0
- sentence-transformers 4.1.0

### Workers (apps/workers/requirements.txt)
- sqlalchemy 2.0.43
- psycopg[binary] 3.2.9
- httpx 0.28.1
- sentence-transformers 4.1.0
- numpy 2.2.6
