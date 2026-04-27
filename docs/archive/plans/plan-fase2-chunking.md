# [REFERENCE] Plan: Fase 2 — Chunking, recuperación a nivel de sección y ranking mejorado

> Este documento queda como referencia tecnica de retrieval/chunking. La fuente activa unica de estado y ejecucion es `docs/master-execution-roadmap.md`.

## Goal
- Introducir fragmentación (chunking) a nivel de sección para legislación, doctrina y corpus regulatorio (BDNS, BORME, CNMV, SEPBLAC).
- Mejorar el ranking de recuperación combinando `ts_rank` sobre chunks con boosts por estructura y enlaces existentes.
- Mantener compatibilidad con `ResultadoEvidencia` y `ConsultaResultado` actuales, añadiendo campos opcionales.
- Ejecutar incrementalmente: nueva migración + backfill standalone + mejoras en retrieval.

## Assumptions / Constraints
- No ORM: el schema se gestiona con SQL puro en Alembic.
- PostgreSQL con `pg_trgm` y `pg_catalog.to_tsvector/to_tsquery('spanish')`.
- La búsqueda actual opera a nivel de documento completo (`version_articulo.texto`, `documento_interpretativo.texto`).
- `search_vector` ya existe en `version_articulo` y `documento_interpretativo` (migración `20260424_0004_doctrina_fulltext`).
- `consulta.py` usa `_build_fragment` (recorte al vuelo) para los fragmentos de evidencia.
- No romper la respuesta de `ResultadoEvidencia` ni `ConsultaResultado`. Campos nuevos como opcionales.

## Research (current state)

### Modules/subprojects involved
- `esdata/alembic/versions/` — migraciones schema
- `esdata/apps/api/services/search.py` — `search_legislacion()` con `ts_rank` sobre `version_articulo`
- `esdata/apps/api/routers/consulta.py` — consulta fiscal (legislación + doctrina + modelos + obligaciones)
- `esdata/apps/api/routers/doctrina.py` — búsqueda doctrina con `ts_headline`
- `esdata/apps/api/routers/buscar.py` — alias de búsqueda
- `esdata/apps/api/schemas.py` — `ResultadoEvidencia`, `ConsultaResultado`, `SearchResult`
- `esdata/apps/workers/boe.py` — ingesta legislación (parsers de BOE)
- `esdata/apps/workers/dgt.py` — ingesta doctrina DGT
- `esdata/apps/workers/teac.py` — ingesta doctrina TEAC
- `esdata/apps/workers/bdns.py`, `borme.py`, `cnmv.py`, `sepblac.py` — corpus regulatorio

### Key files/paths
- `esdata/alembic/versions/20260416_0001_baseline_schema.py` — schema base (norma, articulo, version_articulo, documento_interpretativo, etc.)
- `esdata/alembic/versions/20260424_0004_doctrina_fulltext.py` — añade `search_vector` a `documento_interpretativo`
- `esdata/apps/api/services/search.py:53-188` — `search_legislacion()`: `ts_rank` + `ts_headline` sobre `version_articulo`
- `esdata/apps/api/services/search.py:19-50` — `_build_fragment()`: recorte al vuelo con highlighting
- `esdata/apps/api/routers/consulta.py:263-293` — paso 3: busca legislación via `search_legislacion()`
- `esdata/apps/api/routers/consulta.py:295-336` — paso 4: busca doctrina con `ILIKE` (no fulltext)
- `esdata/apps/api/schemas.py:336-341` — `ResultadoEvidencia`: `source_url`, `fuente_norma`, `fragmento_exacto`, `motivo_ranking`
- `esdata/apps/api/schemas.py:343-371` — `ConsultaResultado`: campos `rank`, `evidencia`, `fragmento`

### Entrypoints (API)
- `GET /v1/consulta` — consulta fiscal inteligente (legislación + doctrina + modelos + obligaciones)
- `GET /v1/buscar/legislacion` — búsqueda legislación (usa `search_legislacion`)
- `GET /v1/buscar/doctrina` — búsqueda doctrina
- `GET /v1/doctrina/{referencia}` — detalle doctrina

### Data models/storage touched
- **Nuevas tablas**: `documento_seccion`, `documento_fragmento`
- **Tablas existentes con search_vector**: `version_articulo`, `documento_interpretativo`
- **Tablas existentes con texto**: `documento_interpretativo`, `bdns_documento`, `borme_acto`, `cnmv_documento`, `sepblac_documento`
- **Tablas de enlace**: `documento_articulo`, `articulo_materia`

### Interfaces/contracts
- `ResultadoEvidencia` — NO romper. Añadir campos opcionales: `chunk_id`, `chunk_type`, `orden_fragmento`.
- `ConsultaResultado` — NO romper. Añadir campos opcionales: `chunk_id`, `seccion`, `anexo`.
- `SearchResult` — NO romper. Añadir campos opcionales: `chunk_id`, `rank`.

### Existing patterns to follow
- Migraciones SQL puras (sin ORM) como `20260416_0001_baseline_schema.py`
- Triggers automáticos para `search_vector` como en `version_articulo` (línea 338-356 del baseline)
- `_build_fragment()` como fallback cuando no hay `ts_headline` (SQLite)
- Workers con `_ensure_schema()` para crear tablas si no existen
- `sync_log` para tracking de ingesta

## Analysis

### Options

#### 8) Granularidad de chunking
- **8b (elegida)**: `documento_seccion` (estructuras naturales) + `documento_fragmento` (retrieval real).
  - `documento_seccion`: divide documentos en capítulos, secciones, partes naturales.
  - `documento_fragmento`: fragmentos de texto optimizados para búsqueda (con `search_vector`).

#### 9) Metadata por chunk
- **9b (elegida)**: metadata completo con `seccion`, `capitulo`, `articulo_referenciado`, `token_count`, `search_vector`.

#### 10) Ranking
- **10c (elegida)**: `ts_rank` del chunk + boost estructural + boost por enlace existente.

### Decision

**Elegida**: 8b + 9b + 10c + incremental + workers existentes primero + compatibilidad extendida.

**Por qué**:
- Dos tablas separadas (`seccion` + `fragmento`) permite navegación jerárquica sin perder precisión en retrieval.
- `search_vector` por chunk es obligatorio para que `ts_rank` tenga sentido.
- El ranking con boosts aprovecha infraestructura ya existente (`documento_articulo`, `articulo_materia`).
- Incremental reduce riesgo: backfill standalone permite rollback sin tocar workers.

### Risks / edge cases
- **Backfill pesado**: si el backfill tarda mucho, separar worker dedicado.
- **Chunking de doctrina**: los documentos DGT no tienen estructura formal de secciones. Fallback a tamaño fijo (2000 chars, 200 overlap).
- **SQLite**: los workers pueden ejecutarse con SQLite en dev. `tsvector` no existe en SQLite. El backfill debe ser condicional.
- **Duplicados**: el backfill debe ser idempotente (DELETE + INSERT por doc_id, o ON CONFLICT DO UPDATE).
- **Ranking en corpus sin estructura**: BDNS, BORME, CNMV, SEPBLAC no tienen artículos ni materias. No hay boost por enlace para ellos.
- **Fragmento corto vs largo**: chunks muy cortos pierden contexto; chunks muy largos pierden precisión. Límite de 2000 chars como fallback.

### Schema propuesto

```sql
-- Secciones naturales del documento (capítulos, partes, secciones)
CREATE TABLE IF NOT EXISTS documento_seccion (
    id SERIAL PRIMARY KEY,
    documento_origen_tipo TEXT NOT NULL,       -- 'version_articulo', 'documento_interpretativo', 'bdns_documento', etc.
    documento_origen_id INTEGER NOT NULL,       -- FK al documento padre
    tipo_seccion TEXT NOT NULL,                 -- 'capitulo', 'seccion', 'parte', 'disposicion', 'articulo'
    numero TEXT,                                -- número de sección (NULL si no aplica)
    titulo TEXT,                                -- título de la sección
    nivel INTEGER DEFAULT 0,                    -- profundidad jerárquica
    orden INTEGER DEFAULT 0,                    -- orden dentro del documento
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documento_seccion_origen
    ON documento_seccion(documento_origen_tipo, documento_origen_id);

CREATE INDEX IF NOT EXISTS idx_documento_seccion_tipo
    ON documento_seccion(tipo_seccion);

-- Fragmentos para retrieval (chunks con search_vector)
CREATE TABLE IF NOT EXISTS documento_fragmento (
    id SERIAL PRIMARY KEY,
    documento_origen_tipo TEXT NOT NULL,        -- 'version_articulo', 'documento_interpretativo', etc.
    documento_origen_id INTEGER NOT NULL,       -- FK al documento padre
    seccion_id INTEGER REFERENCES documento_seccion(id),  -- sección a la que pertenece (NULL si es chunk de texto plano)
    chunk_index INTEGER NOT NULL,               -- índice dentro del documento (0, 1, 2...)
    chunk_type TEXT NOT NULL DEFAULT 'natural', -- 'natural' (estructura), 'size_bound' (tamaño), 'overlap' (solapado)
    titulo TEXT,                                -- título del chunk (si tiene)
    texto TEXT NOT NULL,                        -- texto del chunk
    char_start INTEGER,                         -- posición inicial en el texto original
    char_end INTEGER,                           -- posición final en el texto original
    token_count INTEGER,                        -- número de tokens aproximados
    search_vector TSVECTOR,                     -- vector de búsqueda TSVECTOR
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(documento_origen_tipo, documento_origen_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_documento_fragmento_origen
    ON documento_fragmento(documento_origen_tipo, documento_origen_id);

CREATE INDEX IF NOT EXISTS idx_documento_fragmento_seccion
    ON documento_fragmento(seccion_id);

CREATE INDEX IF NOT EXISTS idx_documento_fragmento_search_vector
    ON documento_fragmento USING GIN (search_vector);

-- Trigger automático para search_vector
CREATE OR REPLACE FUNCTION update_documento_fragmento_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.titulo, '') || ' ' || NEW.texto);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_documento_fragmento_search_vector ON documento_fragmento;
CREATE TRIGGER trg_documento_fragmento_search_vector
    BEFORE INSERT OR UPDATE OF texto, titulo ON documento_fragmento
    FOR EACH ROW
    EXECUTE FUNCTION update_documento_fragmento_search_vector();
```

### Ranking propuesto

```sql
-- search_legislacion mejorada: ts_rank(chunk) + boosts
SELECT df.id AS chunk_id,
       df.documento_origen_tipo,
       df.documento_origen_id,
       df.chunk_index,
       df.texto,
       df.seccion_id,
       ts_rank(df.search_vector, to_tsquery('spanish', :tsquery)) AS chunk_rank,
       -- Boost por enlace existente a artículo
       CASE WHEN EXISTS (
           SELECT 1 FROM documento_articulo da
           JOIN articulo a ON a.id = da.articulo_id
           JOIN norma n ON n.id = a.norma_id
           WHERE n.codigo = :norma AND a.numero = :articulo_num
             AND da.documento_id = :doc_id
       ) THEN 1.5 ELSE 1.0 END AS enlace_boost,
       -- Boost por relevancia estructural (art. 1 > art. 15)
       CASE
           WHEN CAST(:articulo_num AS INTEGER) <= 5 THEN 1.3
           WHEN CAST(:articulo_num AS INTEGER) <= 20 THEN 1.1
           ELSE 1.0
       END AS estructura_boost,
       ts_rank(df.search_vector, to_tsquery('spanish', :tsquery))
           * CASE WHEN EXISTS (...) THEN 1.5 ELSE 1.0 END
           * CASE WHEN CAST(:articulo_num AS INTEGER) <= 5 THEN 1.3 ELSE 1.0 END
           AS final_rank
FROM documento_fragmento df
WHERE df.search_vector @@ to_tsquery('spanish', :tsquery)
ORDER BY final_rank DESC
LIMIT 10;
```

### API: GET /v1/chunks/{id}

```
GET /v1/chunks/{id}

Response:
{
    "id": 123,
    "documento_origen_tipo": "version_articulo",
    "documento_origen_id": 456,
    "chunk_index": 2,
    "chunk_type": "natural",
    "titulo": "Artículo 91. Base imponible",
    "texto": "...",
    "char_start": 1200,
    "char_end": 3400,
    "token_count": 450,
    "seccion": {
        "id": 78,
        "tipo_seccion": "articulo",
        "numero": "91",
        "titulo": "Base imponible",
        "nivel": 1
    },
    "evidencia": {
        "source_url": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-1992-28740",
        "fuente_norma": "BOE-A-1992-28740",
        "fragmento_exacto": "...",
        "motivo_ranking": "ts_rank=0.0234 con boost por enlace"
    }
}
```

### Plan de migraciones

1. **Migración `20260424_0005_chunking_schema.py`**: crea `documento_seccion` + `documento_fragmento` + triggers.
2. **Migración `20260424_0006_chunking_backfill_legacy.py`** (opcional): migra datos existentes de `version_articulo` a `documento_fragmento` si se quiere.

### Plan de backfill

Script standalone: `scripts/backfill_chunks.py`

```python
"""Backfill chunks para todos los corpus.

Ejecuta:
    python scripts/backfill_chunks.py --corpus version_articulo
    python scripts/backfill_chunks.py --corpus documento_interpretativo
    python scripts/backfill_chunks.py --corpus all
    python scripts/backfill_chunks.py --help
"""
```

Estrategia por corpus:

| Corpus | Chunking | Método |
|--------|----------|--------|
| `version_articulo` | Natural | 1 chunk = 1 artículo (ya existe como fila). Crear `documento_seccion` + `documento_fragmento` por fila. |
| `documento_interpretativo` | Híbrido | Intentar dividir por párrafos temáticos. Fallback: 2000 chars, 200 overlap. |
| `bdns_documento` | Híbrido | Intentar dividir por secciones detectadas. Fallback: 2000 chars. |
| `borme_acto` | Híbrido | Intentar dividir por tipo de acto. Fallback: 2000 chars. |
| `cnmv_documento` | Híbrido | Intentar dividir por secciones regulatorias. Fallback: 2000 chars. |
| `sepblac_documento` | Híbrido | Intentar dividir por secciones. Fallback: 2000 chars. |

### Plan de cambios en búsqueda

#### search_legislacion() — `search.py`
- Mantener funcionalidad actual como fallback (SQLite).
- Para PostgreSQL: usar `documento_fragmento` en lugar de `version_articulo` como fuente principal.
- Añadir boosts por `documento_articulo` y `articulo_materia`.
- Devolver `chunk_id`, `chunk_type`, `orden_fragmento` en los resultados.

#### consulta.py — paso 3 (legislación)
- Mantener llamada a `search_legislacion()`.
- Los resultados ya vendrán con `chunk_id` y `fragmento` mejorado.
- Añadir `chunk_id` a `ResultadoEvidencia` como campo opcional.

#### consulta.py — paso 4 (doctrina)
- Mejorar de `ILIKE` a `ts_rank` sobre `documento_fragmento`.
- Si no hay chunks para un documento, fallback a `ILIKE` sobre `documento_interpretativo`.

#### Nuevo endpoint: GET /v1/chunks/{id}
- Retorna un `documento_fragmento` con su `documento_seccion` padre.
- Incluye `evidencia` con `source_url`, `fuente_norma`, `fragmento_exacto`.

### Plan de cambios en schemas.py

```python
class ResultadoEvidencia(BaseModel):
    source_url: str | None
    fuente_norma: str | None
    fragmento_exacto: str | None
    motivo_ranking: str | None
    # Nuevos campos opcionales
    chunk_id: int | None = Field(default=None, description="ID del chunk si aplica")
    chunk_type: str | None = Field(default=None, description="Tipo de chunk: natural, size_bound, overlap")
    orden_fragmento: int | None = Field(default=None, description="Orden del fragmento dentro del documento")

class ConsultaResultado(BaseModel):
    # ... campos existentes ...
    # Nuevos campos opcionales
    chunk_id: int | None = Field(default=None, description="ID del chunk si aplica")
    seccion: str | None = Field(default=None, description="Sección del chunk si aplica")
    anexo: str | None = Field(default=None, description="Anexo del chunk si aplica")
```

## Q&A results (captured)

- Outcome/acceptance criteria:
  - Las búsquedas devuelven chunks con `chunk_id`, `chunk_type`, `orden_fragmento`.
  - `ResultadoEvidencia` mantiene sus 4 campos originales; los nuevos son opcionales.
  - `GET /v1/chunks/{id}` devuelve un chunk con metadata completa.
  - El backfill es idempotente (DELETE + INSERT por doc_id).
  - El ranking mejora con boosts por estructura y enlaces.

- Scope boundaries:
  - Incluye: legislación, doctrina, BDNS, BORME, CNMV, SEPBLAC.
  - No incluye: obligaciones (3b — no FK a chunks por ahora).
  - No incluye: list/filter de chunks (solo GET /v1/chunks/{id} en esta iteración).

- Constraints/non-goals:
  - No romper `ResultadoEvidencia` ni `ConsultaResultado`.
  - Backfill standalone, no acoplado a workers.
  - Workers existentes primero; worker separado solo si backfill pesa demasiado.

- Known modules/paths/subprojects:
  - `esdata/alembic/versions/` — migraciones
  - `esdata/apps/api/services/search.py` — búsqueda legislación
  - `esdata/apps/api/routers/consulta.py` — consulta fiscal
  - `esdata/apps/api/routers/doctrina.py` — búsqueda doctrina
  - `esdata/apps/api/schemas.py` — modelos Pydantic
  - `esdata/apps/workers/boe.py` — ingesta legislación
  - `esdata/apps/workers/dgt.py`, `teac.py` — ingesta doctrina
  - `esdata/apps/workers/bdns.py`, `borme.py`, `cnmv.py`, `sepblac.py` — corpus regulatorio

- Decisions made in Q&A:
  - 1d: todos los corpus
  - 2c: híbrida (estructura natural + fallback tamaño)
  - 3b: no FK a chunks en obligaciones
  - 4c: mejorar consulta + nuevo endpoint GET /v1/chunks/{id}
  - 5: incremental
  - 6: workers existentes primero
  - 7: compatibilidad extendida
  - 8b: documento_seccion + documento_fragmento
  - 9b: metadata completo con search_vector
  - 10c: ts_rank + boosts
  - 11: backfill standalone
  - 12: GET /v1/chunks/{id} primero, list/filter después

## Implementation plan

### Fase 2.1 — Schema y migración
1. Crear `alembic/versions/20260424_0005_chunking_schema.py`
   - Crear `documento_seccion` con índices
   - Crear `documento_fragmento` con `search_vector` + trigger + índice GIN
   - No borrar datos existentes

### Fase 2.2 — Backfill standalone
2. Crear `scripts/backfill_chunks.py`
   - Soporte `--corpus version_articulo|documento_interpretativo|bdns|borme|cnmv|sepblac|all`
   - Para `version_articulo`: 1 chunk = 1 artículo (mapeo directo)
   - Para `documento_interpretativo`: dividir por párrafos temáticos, fallback 2000 chars
   - Para corpus regulatorio: intentar secciones detectadas, fallback 2000 chars
   - Idempotente: DELETE `documento_fragmento` WHERE `documento_origen_tipo` + `documento_origen_id`
   - Log de progreso: chunks creados, errores, tiempo

### Fase 2.3 — Mejora de búsqueda
3. Mejorar `services/search.py::search_legislacion()`
   - Para PostgreSQL: usar `documento_fragmento` como fuente principal
   - Añadir `ts_rank` sobre `df.search_vector`
   - Añadir boost por `documento_articulo` enlace existente
   - Añadir boost por relevancia estructural (art. 1-5 > art. 15+)
   - Mantener fallback ILIKE para SQLite
   - Devolver `chunk_id`, `chunk_type`, `orden_fragmento` en resultados

4. Mejorar `routers/consulta.py::paso_4` (doctrina)
   - Cambiar de `ILIKE` a `ts_rank` sobre `documento_fragmento`
   - Fallback a `ILIKE` sobre `documento_interpretativo` si no hay chunks

### Fase 2.4 — Nuevo endpoint chunks
5. Crear `routers/chunks.py`
   - `GET /v1/chunks/{id}` — devuelve chunk con metadata, sección padre, evidencia
   - Incluir `evidencia` con `source_url`, `fuente_norma`, `fragmento_exacto`

### Fase 2.5 — Schemas
6. Actualizar `schemas.py`
   - `ResultadoEvidencia`: añadir `chunk_id`, `chunk_type`, `orden_fragmento` como opcionales
   - `ConsultaResultado`: añadir `chunk_id`, `seccion`, `anexo` como opcionales
   - `SearchResult`: añadir `chunk_id` como opcional

### Fase 2.6 — Integración workers (post-backfill)
7. En `boe.py::run_sync()`: después de upsert articulo, crear `documento_seccion` + `documento_fragmento`
   - Para `version_articulo`: 1 chunk = 1 artículo
8. En `dgt.py`/`teac.py`: después de upsert doctrine, crear chunks con división por párrafos
9. En `bdns.py`/`borme.py`/`cnmv.py`/`sepblac.py`: crear chunks al ingestar documentos

### Fase 2.7 — Testing y validación
10. Tests de unitarios para chunking logic
11. Tests de integración para `search_legislacion()` con chunks
12. Validación de ranking: comparar resultados antes/después de chunks

## Tests to run
- `pytest esdata/apps/api/` — tests API existentes (no romper)
- `pytest esdata/apps/workers/` — tests workers existentes (no romper)
- Tests nuevos:
  - `test_backfill_chunks.py` — idempotencia, varios corpora
  - `test_search_chunks.py` — ranking con boosts
  - `test_chunks_endpoint.py` — GET /v1/chunks/{id}
