# MCP Fase 4.3 Row Completeness/Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist row-level completeness/provenance for `AEAT`, `CNMV`, and `DGT` rows without changing `/v1/sources/manifest` or `/v1/sources/freshness` behavior in this slice.

**Architecture:** Add one Alembic revision that extends `modelo_recurso` and `documento_interpretativo` with `row_completeness` and `row_provenance`, backfilling existing rows conservatively. Then update the three worker persistence paths so new successful writes stamp strong values (`complete` + `official_exact`) while `source_manifest` stays source-level and only gains a guardrail test/comment.

**Tech Stack:** Python 3.12, SQLAlchemy Core, Alembic, FastAPI services, pytest, Ruff

**Repo Note:** Do not commit or push as part of this plan unless the user explicitly asks.

---

## File Map

- Create: `alembic/versions/20260504_0058_row_completeness_provenance.py`
  Adds the new row-quality columns and conservative backfill/constraints.
- Modify: `apps/api/tests/test_alembic_integrity.py`
  Locks the migration file and required SQL fragments.
- Modify: `apps/workers/aeat_models.py:671-785`
  Stamps `row_completeness` / `row_provenance` on successful `modelo_recurso` inserts.
- Modify: `apps/workers/tests/test_aeat_models.py:680-777`
  Extends the SQLite fixture schema and adds a regression for the AEAT row-quality contract.
- Modify: `apps/workers/cnmv.py:945-1017`
  Extends CNMV upsert defaults/columns to write row-quality when the table supports it.
- Modify: `apps/workers/tests/test_cnmv.py:380-519`
  Adds a row-quality regression for `documento_interpretativo` and keeps the existing sync guardrail.
- Modify: `apps/workers/dgt.py:264-300`
  Refactors DGT upsert to dynamic columns like CNMV so new row-quality columns are written without breaking slim SQLite test tables.
- Modify: `apps/workers/tests/test_dgt.py:92-137`
  Adds a DGT row-quality regression on the direct upsert path.
- Modify: `apps/api/services/source_manifest.py:150-169`
  Adds a short inline clarification that `4.3` remains source-level and ignores row-level fields.
- Modify: `apps/api/routers/source_manifest.py:1-25`
  Keeps endpoint docstrings/comments aligned with the persistence-only decision.
- Modify: `apps/api/tests/test_source_manifest.py`
  Adds a guardrail test proving `get_source_manifest()` stays source-level and does not leak `row_completeness`/`row_provenance`.
- Modify: `docs/master-execution-roadmap.md`
  Closes `4.3` with evidence and moves the next exact step to `4.4`.
- Modify: `docs/operations/agent-notes.md`
  Records the new invariant that row-quality belongs to the row table, not `source_revision` or `sync_log`.

### Task 1: Lock the migration contract and create the Alembic revision

**Files:**
- Create: `alembic/versions/20260504_0058_row_completeness_provenance.py`
- Modify: `apps/api/tests/test_alembic_integrity.py`
- Reference: `alembic/versions/20260504_0056_modelo_articulo_provenance.py`
- Reference: `docs/superpowers/specs/2026-05-04-mcp-fase-4-3-row-completeness-provenance-design.md`

- [ ] **Step 1: Add the failing Alembic integrity regression**

```python
def test_row_quality_columns_are_migrated_in_revision_0058():
    revision_path = (
        ALEMBIC_VERSIONS / "20260504_0058_row_completeness_provenance.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "ADD COLUMN IF NOT EXISTS row_completeness TEXT",
        "ADD COLUMN IF NOT EXISTS row_provenance TEXT",
        "UPDATE modelo_recurso",
        "official_exact",
        "UPDATE documento_interpretativo",
        "official_best_effort",
        "ALTER TABLE modelo_recurso ALTER COLUMN row_completeness SET NOT NULL",
        "ALTER TABLE modelo_recurso ALTER COLUMN row_provenance SET NOT NULL",
        "ALTER TABLE documento_interpretativo ALTER COLUMN row_completeness SET NOT NULL",
        "ALTER TABLE documento_interpretativo ALTER COLUMN row_provenance SET NOT NULL",
        "ck_modelo_recurso_row_completeness",
        "ck_modelo_recurso_row_provenance",
        "ck_documento_interpretativo_row_completeness",
        "ck_documento_interpretativo_row_provenance",
    ):
        assert fragment in contents
```

- [ ] **Step 2: Run the targeted integrity regression to verify red**

Run: `python -m pytest apps/api/tests/test_alembic_integrity.py -q -k "row_quality_columns_are_migrated_in_revision_0058"`

Expected: FAIL with `FileNotFoundError` or assertion failure because revision `0058` does not exist yet.

- [ ] **Step 3: Create the new Alembic revision with conservative backfill**

```python
"""add row-level completeness/provenance to worker-owned source rows

# Revision ID: 20260504_0058_row_completeness_provenance
# Revises: 20260504_0057_dgt_queue_split
# Create Date: 2026-05-04 01:30:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260504_0058_row_completeness_provenance"
down_revision = "20260504_0057_dgt_queue_split"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE modelo_recurso ADD COLUMN IF NOT EXISTS row_completeness TEXT"))
    op.execute(sa.text("ALTER TABLE modelo_recurso ADD COLUMN IF NOT EXISTS row_provenance TEXT"))
    op.execute(sa.text("ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS row_completeness TEXT"))
    op.execute(sa.text("ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS row_provenance TEXT"))

    op.execute(
        sa.text(
            """
            UPDATE modelo_recurso
            SET row_completeness = COALESCE(row_completeness, 'complete'),
                row_provenance = COALESCE(row_provenance, 'official_exact')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE documento_interpretativo
            SET row_completeness = COALESCE(row_completeness, 'partial'),
                row_provenance = COALESCE(row_provenance, 'official_best_effort')
            """
        )
    )

    op.execute(sa.text("ALTER TABLE modelo_recurso ALTER COLUMN row_completeness SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE modelo_recurso ALTER COLUMN row_provenance SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE documento_interpretativo ALTER COLUMN row_completeness SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE documento_interpretativo ALTER COLUMN row_provenance SET NOT NULL"))

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE modelo_recurso
                ADD CONSTRAINT ck_modelo_recurso_row_completeness
                CHECK (row_completeness IN ('complete', 'partial'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE modelo_recurso
                ADD CONSTRAINT ck_modelo_recurso_row_provenance
                CHECK (row_provenance IN ('official_exact', 'official_best_effort'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE documento_interpretativo
                ADD CONSTRAINT ck_documento_interpretativo_row_completeness
                CHECK (row_completeness IN ('complete', 'partial'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE documento_interpretativo
                ADD CONSTRAINT ck_documento_interpretativo_row_provenance
                CHECK (row_provenance IN ('official_exact', 'official_best_effort'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo DROP CONSTRAINT IF EXISTS ck_documento_interpretativo_row_provenance"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo DROP CONSTRAINT IF EXISTS ck_documento_interpretativo_row_completeness"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso DROP CONSTRAINT IF EXISTS ck_modelo_recurso_row_provenance"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso DROP CONSTRAINT IF EXISTS ck_modelo_recurso_row_completeness"
        )
    )
    op.execute(sa.text("ALTER TABLE documento_interpretativo DROP COLUMN IF EXISTS row_provenance"))
    op.execute(sa.text("ALTER TABLE documento_interpretativo DROP COLUMN IF EXISTS row_completeness"))
    op.execute(sa.text("ALTER TABLE modelo_recurso DROP COLUMN IF EXISTS row_provenance"))
    op.execute(sa.text("ALTER TABLE modelo_recurso DROP COLUMN IF EXISTS row_completeness"))
```

- [ ] **Step 4: Run the Alembic integrity file to verify green**

Run: `python -m pytest apps/api/tests/test_alembic_integrity.py -q`

Expected: PASS, including the new `0058` regression.

### Task 2: Stamp strong row-quality on successful AEAT resource rows

**Files:**
- Modify: `apps/workers/aeat_models.py:671-785`
- Modify: `apps/workers/tests/test_aeat_models.py:680-777`
- Reference: `alembic/versions/20260501_0054_aeat_modelo_recurso.py`

- [ ] **Step 1: Extend the SQLite test fixture schema and add a failing AEAT row-quality regression**

```python
def _setup_db(self):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE modelo_recurso (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    tipo_recurso TEXT NOT NULL,
                    formato TEXT NOT NULL,
                    url_recurso TEXT NOT NULL,
                    sha256_contenido TEXT NOT NULL,
                    etag TEXT,
                    last_modified TEXT,
                    content_length INTEGER,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    row_completeness TEXT NOT NULL,
                    row_provenance TEXT NOT NULL,
                    activa INTEGER NOT NULL DEFAULT 1,
                    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(campana_id, tipo_recurso, sha256_contenido)
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX idx_modelo_recurso_activa_unica ON modelo_recurso (campana_id, tipo_recurso) WHERE activa = 1"
            )
        )
    return engine


def test_inserted_resource_sets_row_quality_contract(self):
    engine = self._setup_db()
    with engine.begin() as conn:
        assert _store_modelo_recurso_version(
            conn,
            1,
            "instrucciones",
            "pdf",
            "https://example.com/a.pdf",
            b"same",
        ) == "inserted"
        row = conn.execute(
            text(
                "SELECT row_completeness, row_provenance FROM modelo_recurso WHERE campana_id = 1 AND tipo_recurso = 'instrucciones'"
            )
        ).fetchone()

    assert row == ("complete", "official_exact")
```

- [ ] **Step 2: Run the AEAT resource-versioning slice to verify red**

Run: `python -m pytest apps/workers/tests/test_aeat_models.py -q -k "inserted_resource_sets_row_quality_contract or TestRecursoVersioning"`

Expected: FAIL with `NOT NULL constraint failed: modelo_recurso.row_completeness` because the insert path does not write the new columns yet.

- [ ] **Step 3: Write the minimal AEAT persistence change**

```python
conn.execute(
    text(
        """
        INSERT INTO modelo_recurso (
            campana_id,
            tipo_recurso,
            formato,
            url_recurso,
            sha256_contenido,
            etag,
            last_modified,
            content_length,
            metadata,
            row_completeness,
            row_provenance,
            activa,
            first_seen_at,
            last_seen_at
        )
        VALUES (
            :campana_id,
            :tipo_recurso,
            :formato,
            :url_recurso,
            :sha256,
            :etag,
            :last_modified,
            :content_length,
            CAST(:metadata AS JSON),
            :row_completeness,
            :row_provenance,
            true,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """
    ),
    {
        "campana_id": campana_id,
        "tipo_recurso": tipo_recurso,
        "formato": formato,
        "url_recurso": url_recurso,
        "sha256": sha256,
        "etag": metadata.get("etag") if metadata else None,
        "last_modified": metadata.get("last_modified") if metadata else None,
        "content_length": metadata.get("content_length") if metadata else None,
        "metadata": json.dumps(metadata or {}),
        "row_completeness": "complete",
        "row_provenance": "official_exact",
    },
)
```

- [ ] **Step 4: Re-run the AEAT versioning slice to verify green**

Run: `python -m pytest apps/workers/tests/test_aeat_models.py -q -k "inserted_resource_sets_row_quality_contract or TestRecursoVersioning"`

Expected: PASS.

### Task 3: Stamp row-quality on CNMV successful document upserts

**Files:**
- Modify: `apps/workers/cnmv.py:945-1017`
- Modify: `apps/workers/tests/test_cnmv.py:380-519`
- Reference: `alembic/versions/20260426_0023_cnmv_enriched_metadata.py`

- [ ] **Step 1: Add the failing CNMV upsert regression with the new row columns**

```python
def test_upsert_documento_interpretativo_sets_row_quality_contract():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    numero_circular TEXT,
                    fecha_publicacion TEXT,
                    referencia_boe TEXT,
                    estado_vigencia TEXT,
                    row_completeness TEXT NOT NULL,
                    row_provenance TEXT NOT NULL
                )
                """
            )
        )

        payload = {
            "referencia": "BOE-A-2009-133",
            "fecha": "2009-01-02",
            "titulo": "Circular 9/2008",
            "tipo_documento": "circular_cnmv",
            "organismo_emisor": "CNMV",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
            "ambito": "reporting_regulatorio_cnmv",
            "texto": "Normas contables.",
            "url_fuente": "https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133",
            "numero_circular": "9/2008",
            "fecha_publicacion": "2009",
            "referencia_boe": "BOE-A-2009-133",
            "estado_vigencia": "vigente",
        }

        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT row_completeness, row_provenance FROM documento_interpretativo WHERE referencia = 'BOE-A-2009-133'"
            )
        ).fetchone()

    assert row == ("complete", "official_exact")
```

- [ ] **Step 2: Run the focused CNMV regression to verify red**

Run: `python -m pytest apps/workers/tests/test_cnmv.py -q -k "upsert_documento_interpretativo_sets_row_quality_contract"`

Expected: FAIL with `NOT NULL constraint failed: documento_interpretativo.row_completeness` because CNMV does not write the new fields yet.

- [ ] **Step 3: Extend CNMV defaults and dynamic columns minimally**

```python
payload.setdefault("row_completeness", "complete")
payload.setdefault("row_provenance", "official_exact")

columns = [
    "tipo_documento",
    "organismo_emisor",
    "jurisdiccion",
    "tipo_fuente",
    "ambito",
    "referencia",
    "fecha",
    "titulo",
    "texto",
    "url_fuente",
]
for col in (
    "numero_circular",
    "fecha_publicacion",
    "referencia_boe",
    "estado_vigencia",
    "row_completeness",
    "row_provenance",
):
    if col in payload:
        columns.append(col)
```

- [ ] **Step 4: Re-run the CNMV persistence slice to verify green**

Run: `python -m pytest apps/workers/tests/test_cnmv.py -q -k "upsert_documento_interpretativo_sets_row_quality_contract or run_sync_persists_cnmv_document_and_metrics"`

Expected: PASS.

### Task 4: Refactor DGT upsert to support row-quality without breaking slim SQLite tests

**Files:**
- Modify: `apps/workers/dgt.py:264-300`
- Modify: `apps/workers/tests/test_dgt.py:92-137`
- Reference: `apps/workers/cnmv.py:945-1017`

- [ ] **Step 1: Add the failing DGT row-quality regression**

```python
def test_upsert_documento_interpretativo_sets_row_quality_contract():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    row_completeness TEXT NOT NULL,
                    row_provenance TEXT NOT NULL
                )
                """
            )
        )

        payload = {
            "referencia": "V2274-22",
            "fecha": "2022-10-27",
            "titulo": "Consulta DGT sobre NFTs e IVA",
            "texto": "Documento relacionado con la Ley del IVA.",
            "url_fuente": "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2274-22",
        }

        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT row_completeness, row_provenance FROM documento_interpretativo WHERE referencia = 'V2274-22'"
            )
        ).fetchone()

    assert row == ("complete", "official_exact")
```

- [ ] **Step 2: Run the focused DGT regression to verify red**

Run: `python -m pytest apps/workers/tests/test_dgt.py -q -k "upsert_documento_interpretativo_sets_row_quality_contract"`

Expected: FAIL because the current DGT insert does not include the new NOT NULL columns.

- [ ] **Step 3: Replace the fixed DGT insert with CNMV-style dynamic column handling**

```python
def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
    if conn.engine.dialect.name == "sqlite":
        table_columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(documento_interpretativo)"))
        }
    else:
        table_columns = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'documento_interpretativo'
                    """
                )
            )
        }

    payload = {
        "tipo_documento": "consulta_vinculante",
        "organismo_emisor": "DGT",
        "jurisdiccion": "es",
        "tipo_fuente": "dgt",
        "ambito": "fiscal",
        "row_completeness": payload.get("row_completeness", "complete"),
        "row_provenance": payload.get("row_provenance", "official_exact"),
        **payload,
    }

    columns = [
        "tipo_documento",
        "organismo_emisor",
        "jurisdiccion",
        "tipo_fuente",
        "ambito",
        "referencia",
        "fecha",
        "titulo",
        "texto",
        "url_fuente",
        "row_completeness",
        "row_provenance",
    ]
    columns = [col for col in columns if col in table_columns]

    placeholders = ", ".join(f":{col}" for col in columns)
    cols_str = ", ".join(columns)
    update_cols = ", ".join(f"{col} = excluded.{col}" for col in columns if col != "referencia")

    conn.execute(
        text(
            f"""
            INSERT INTO documento_interpretativo ({cols_str})
            VALUES ({placeholders})
            ON CONFLICT (referencia) DO UPDATE SET
                {update_cols}
            """
        ),
        payload,
    )
```

- [ ] **Step 4: Re-run the DGT persistence and 4.2 guardrails to verify green**

Run: `python -m pytest apps/workers/tests/test_dgt.py -q -k "upsert_documento_interpretativo_sets_row_quality_contract or upsert_documento_interpretativo_is_idempotent_and_stores_dgt_fields or marks_partial_when_dgt_search_returns_no_results"`

Expected: PASS.

### Task 5: Keep `source_manifest` explicitly source-level in `4.3`

**Files:**
- Modify: `apps/api/services/source_manifest.py:150-169`
- Modify: `apps/api/routers/source_manifest.py:1-25`
- Modify: `apps/api/tests/test_source_manifest.py`

- [ ] **Step 1: Add the source-level guardrail test**

```python
from sqlalchemy import create_engine, text


def test_get_source_manifest_remains_source_level_when_row_quality_exists(monkeypatch):
    from services import source_manifest

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO sync_log (worker, started_at, finished_at, status)
                VALUES ('worker-cnmv', '2026-05-04T00:00:00+00:00', '2026-05-04T00:05:00+00:00', 'ok')
                """
            )
        )

    monkeypatch.setattr(source_manifest, "ensure_governance_tables", lambda: None)
    monkeypatch.setattr(
        source_manifest,
        "_parse_manifest",
        lambda: [
            {
                "source_id": "cnmv",
                "fuente": "CNMV",
                "referencia_canonica": "https://www.cnmv.es/",
                "tipo": "regulatorio",
                "prioridad": "alta",
                "estado_actual_repo": "ingestado",
                "estado_objetivo": "operativo",
                "owner": "compliance",
                "trust_tier": "official-primary",
                "cadencia": "weekly",
                "modo_deteccion_cambios": "sha256",
                "worker": "worker-cnmv",
                "stale_after_hours": 24 * 8,
            }
        ],
    )

    with engine.begin() as conn:
        sources = source_manifest.get_source_manifest(conn)

    assert sources[0]["last_status"] == "ok"
    assert "row_completeness" not in sources[0]
    assert "row_provenance" not in sources[0]
```

- [ ] **Step 2: Run the source-manifest test file to establish the guardrail**

Run: `python -m pytest apps/api/tests/test_source_manifest.py -q`

Expected: PASS before the code comment/docstring change.

- [ ] **Step 3: Add one explicit code comment/docstring clarifying the 4.3 boundary**

```python
"""Source manifest and freshness ledger service.

MCP 4.3 is persistence-only for row-level completeness/provenance.
This service remains source-level until a later aggregation slice wires
row-quality into `/v1/sources/*` explicitly.
"""
```

```python
"""Source manifest and freshness endpoints.

These endpoints stay source-level in MCP 4.3; row-level completeness and
provenance live only in worker-owned tables for now.
"""
```

- [ ] **Step 4: Re-run the source-manifest test file to verify stability**

Run: `python -m pytest apps/api/tests/test_source_manifest.py -q`

Expected: PASS with unchanged payload behavior.

### Task 6: Run final verification and close the phase in active docs

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`

- [ ] **Step 1: Run the full 4.3 verification set**

Run: `python -m pytest apps/api/tests/test_alembic_integrity.py apps/api/tests/test_source_manifest.py apps/workers/tests/test_aeat_models.py apps/workers/tests/test_cnmv.py apps/workers/tests/test_dgt.py -q`

Expected: PASS.

Run: `python -m ruff check alembic/versions/20260504_0058_row_completeness_provenance.py apps/api/services/source_manifest.py apps/api/routers/source_manifest.py apps/api/tests/test_alembic_integrity.py apps/api/tests/test_source_manifest.py --select F,I`

Expected: `All checks passed!`

Run: `python -m ruff check apps/workers/aeat_models.py apps/workers/cnmv.py apps/workers/dgt.py apps/workers/tests/test_aeat_models.py apps/workers/tests/test_cnmv.py apps/workers/tests/test_dgt.py --select F`

Expected: `All checks passed!`

- [ ] **Step 2: Update the roadmap live summary and 4.3 history note**

```markdown
- Objetivo actual: abrir **Fase 4.4** del plan MCP y separar enlaces heurísticos de exactos en retrieval/links documentales.
- Estado actual: **Fase 4.3** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`.
- Estado del agente activo: `modelo_recurso` y `documento_interpretativo` ya persisten `row_completeness` / `row_provenance`; `source_manifest` sigue estable y source-level en este slice.
- Siguiente paso exacto: abrir **Fase 4.4** del plan MCP y separar enlaces heurísticos de exactos en `boe`, `borme` y retrieval relacionado, segun `docs/reference/mcp-remediation-plan.md`.
```

- [ ] **Step 3: Add one reusable agent note about the new row-quality boundary**

```markdown
### 2026-05-04 - Fase 4.3 row-quality: completeness/provenance vive en la tabla duena de la fila

- Scope: `modelo_recurso`, `documento_interpretativo`, `source_revision`, `sync_log`, `source_manifest`
- Hallazgo: status de sync, revision por hash y row-quality son contratos distintos. Si se mezclan, ops/API/retrieval pueden sobreinterpretar la calidad real de una fila o de un run.
- Impacto: meter completeness/provenance en `source_revision` o inferirla solo desde `sync_log` hace que una revision tecnica o un resultado de run parezcan garantia de calidad por fila cuando no lo son.
- Regla practica: guardar `row_completeness` / `row_provenance` en la tabla que posee la fila persistida; reservar `source_revision` para cambios tecnicos y `sync_log` para outcomes del run. `source_manifest` debe seguir source-level hasta que exista un slice explicito de agregacion row-level.
```

- [ ] **Step 4: Re-run the two doc-adjacent tests after the documentation update**

Run: `python -m pytest apps/api/tests/test_alembic_integrity.py apps/api/tests/test_source_manifest.py -q`

Expected: PASS.
