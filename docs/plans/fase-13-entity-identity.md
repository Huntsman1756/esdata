# Plan: Fase 13 — Identidad de entidad y LEI / vLEI

## Goal
- Implementar tabla `entity_identifiers` con FK a `empresa` para LEI, nombre legal, país, estado y vigencia
- Preparar superficie vLEI (columnas placeholder documentadas como extensibles)
- Crear worker de lookup LEI via GLEIF API
- Crear router `/v1/entidades` con endpoints `GET /lei/{lei}` y `GET /buscar?q=...`
- Tests de normalización y lookup

## Assumptions / constraints
- Tabla separada `entity_identifiers` con FK a `empresa.id`
- vLEI: superficie preparada (columnas placeholder), sin lógica de validación
- GLEIF API pública como fuente de lookup
- Nuevo router `/v1/entidades` independiente de `/v1/empresas`
- Raw SQL `op.execute()` para migración Alembic (patrón baseline)
- No acoplar ownership/sanciones/LEI en tabla monolítica
- Patrón: `raw-source -> normalized identity -> db -> api`

## Research (current state)
- **Módulos involucrados:**
  - `alembic/versions/` — migraciones DB
  - `apps/api/routers/` — routers FastAPI
  - `apps/api/schemas.py` — modelos Pydantic
  - `apps/workers/` — workers de ingesta
  - `apps/api/tests/` — tests

- **Key files/paths:**
  - `alembic/versions/20260416_0001_baseline_schema.py` — patrón raw SQL
  - `apps/api/routers/empresas.py` — router existente para referencia
  - `apps/api/schemas.py` — schemas existentes (EmpresaSummary, etc.)
  - `apps/api/main.py:148` — router mounting
  - `apps/workers/borme.py` — patrón worker existente
  - `apps/api/tests/conftest.py:460-478` — fixtures SQLite
  - `apps/api/tests/test_smoke.py:981` — tests empresas existentes

- **Entrypoints:**
  - API: `GET /v1/entidades/lei/{lei}`, `GET /v1/entidades/buscar?q=...`
  - Worker: `apps/workers/entity_identity.py` (nuevo)

- **Data models/storage:**
  - Nueva tabla `entity_identifiers` con FK a `empresa`
  - Columnas: `empresa_id`, `lei`, `nombre_legal`, `pais`, `estado`, `vigencia_desde`, `vigencia_hasta`, `vlei_status`, `vlei_cred_url`, `fuente_ref`, `created_at`
  - Tabla `entity_aliases` para aliases normalizados con `empresa_id`, `alias`, `alias_normalizado`, `fuente`, `confianza`

- **Existing patterns to follow:**
  - Migraciones: `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `IF NOT EXISTS` para idempotencia
  - Workers: argparse CLI, httpx.Client, sqlalchemy create_engine, log_sync()
  - Routers: APIRouter prefix="/v1/entidades", tags=["entidades"], db_session context manager
  - Tests: pytest-asyncio + AsyncClient + SQLite fixture

## Analysis
### Options
1) Tabla separada `entity_identifiers` + `entity_aliases` (DECIDIDO)
2) Extender `empresa` con columnas LEI/vLEI
3) Ambas

### Decision
- Elegido: Tabla separada `entity_identifiers` con FK a `empresa`
- Por qué: Separa concerns (identidad vs documentos), prepara vLEI sin acoplar, sigue patrón `documento_empresa` como junction table

### Risks / edge cases
- GLEIF API rate limits: implementar backoff y cache local
- LEI no disponible para todas las empresas españolas: campo nullable, fallback a NIF
- vLEI: superficie placeholder sin validación real — documentar limitación
- Migraciones idempotentes: `IF NOT EXISTS` en todas las tablas
- SQLite test DB: verificar compatibilidad de columnas TIMESTAMPTZ

### Open questions
- (none — Q&A resuelto: 1a 2a 3a 4a 5a)

## Q&A results (captured after the session)
- Outcome/acceptance criteria:
  1. Entidad resoluble por LEI con metadata mínima confiable
  2. Sistema soporta aliases y nombres legales normalizados
  3. Superficie vLEI documentada como extensible sin bloquear MVP
  4. Tests verdes
- Scope boundaries:
  - Solo LEI básico + aliases + superficie vLEI placeholder
  - No matching avanzado (eso va en Fase 14+)
  - No ownership/sanciones acopladas
- Constraints/non-goals:
  - GLEIF API como referencia, no reemplazo de registros oficiales españoles
  - No exponer payloads brutos: normalizar primero, persistir, luego servir por API
- Known modules/paths/subprojects:
  - alembic, routers, schemas, workers, tests
- Decisions made in Q&A:
  1. Tabla separada entity_identifiers con FK a empresa
  2. vLEI: superficie preparada (columnas placeholder)
  3. GLEIF API pública como fuente
  4. Nuevo router /v1/entidades independiente
  5. Raw SQL op.execute() para migración
- Remaining open questions:
  - (none)

## Implementation plan

### Paso 1: Migración Alembic — tablas entity_identifiers y entity_aliases
- Archivo: `alembic/versions/20260426_0011_entity_identity.py`
- Tablas:
  - `entity_identifiers`: id (UUID), empresa_id (INT FK), lei (TEXT, unique index), nombre_legal, pais (CHAR2), estado (TEXT), vigencia_desde (DATE), vigencia_hasta (DATE), vlei_status (TEXT), vlei_cred_url (TEXT), fuente_ref (TEXT), created_at
  - `entity_aliases`: id (UUID), empresa_id (INT FK), alias (TEXT), alias_normalizado (TEXT), fuente (TEXT), confianza (NUMERIC), created_at
- Índices: lei_trgm, alias_normalizado_trgm, empresa_id en ambas tablas
- Patrón: raw SQL `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`

### Paso 2: Schemas Pydantic para respuestas
- Archivos: `apps/api/schemas.py`
- Modelos: `EntityIdentifier`, `EntityIdentifierDetail`, `EntityAlias`, `EntitySearchResult`, `EntityLeiResponse`, `EntitySearchResponse`
- Seguir patrón existente: `EmpresaDetail`, `EmpresaSummary`, etc.

### Paso 3: Router `/v1/entidades`
- Archivo: `apps/api/routers/entidades.py` (nuevo)
- Endpoints:
  - `GET /v1/entidades/lei/{lei}` — lookup por LEI
  - `GET /v1/entidades/buscar?q=...` — búsqueda por nombre/alias aproximado
  - `GET /v1/entidades/{empresa_id}` — detalle de entidad con identificadores
- Mounting: `app.include_router(entidades.router)` en `main.py`
- Tags: `["entidades"]`

### Paso 4: Worker de lookup LEI via GLEIF API
- Archivo: `apps/workers/entity_identity.py` (nuevo)
- Función: `lookup_lei(empresa_id, empresa_nombre)` que llama GLEIF API
- Patrón: argparse CLI, httpx.Client, sqlalchemy engine, log_sync()
- Endpoint GLEIF: `https://api.gleif.org/api/v1/lei-records?filter[lei]=...` o search por nombre
- Normalización: convertir response GLEIF -> entity_identifiers row
- vLEI: dejar campos placeholder sin lógica de validación

### Paso 5: Fixtures y seed en conftest.py
- Tablas SQLite: `entity_identifiers` y `entity_aliases` en `conftest.py`
- Seed data: 1-2 empresas con LEI de ejemplo para tests
- Asegurar compatibilidad con SQLite (TEXT para timestamps, AUTOINCREMENT)

### Paso 6: Tests
- Archivo: `apps/api/tests/test_entity_identity.py` (nuevo)
- Tests:
  - `test_lookup_lei_valido` — endpoint /lei/{lei} devuelve entidad
  - `test_lookup_lei_no_existe` — 404 para LEI inexistente
  - `test_buscar_por_nombre` — endpoint /buscar?q= devuelve resultados
  - `test_buscar_por_alias` — búsqueda por alias normalizado
  - `test_detalle_empresa_con_identificadores` — endpoint /{empresa_id} incluye entity_identifiers
  - `test_normalizacion_alias` — función de normalización de aliases

### Paso 7: Actualizar master-execution-roadmap.md
- Marcar Fase 13 como `COMPLETA`
- Actualizar resumen vivo y siguiente paso

## Tests to run
- `pytest apps/api/tests/test_entity_identity.py -v` — tests específicos
- `pytest apps/api/tests/test_smoke.py -v` — smoke tests (verificar que no se rompen endpoints existentes)
- `alembic upgrade head` — verificar migración
- `alembic downgrade -1` — verificar downgrade
