# MCP Fase 4.1 DGT Queue Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split DGT queue state into a dedicated `dgt_queue` table so `source_revision` stores only real revision hashes for DGT `consulta` entities.

**Architecture:** Add one migration-owned `dgt_queue` table, keep a local SQLite-only bootstrap helper in `apps/workers/dgt.py`, and move seed/discovery/process queue operations off `source_revision`. Preserve `check_content_changed()` and `record_revision()` as the only revision writers.

**Tech Stack:** Python 3.12, SQLAlchemy, Alembic, pytest, Ruff

---

### Task 1: Add failing DGT tests for queue/revision separation

**Files:**
- Modify: `apps/workers/tests/test_dgt.py`
- Reference: `docs/superpowers/specs/2026-05-04-mcp-fase-4-1-dgt-queue-design.md`

- [ ] **Step 1: Add a red unit test for seed queue storage**

```python
def test_queue_seed_entries_live_in_dgt_queue_not_source_revision():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as conn:
        ensure_source_revision_table(conn)
        _create_dgt_queue_table(conn)

        url = "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0001-26"
        _ensure_dgt_queue(conn, "worker-dgt", [url])

        pending = _get_pending_urls(conn, "worker-dgt")
        queue_rows = conn.execute(
            text("SELECT source_entity_id, dgt_url, status FROM dgt_queue")
        ).fetchall()
        source_rows = conn.execute(
            text("SELECT source_entity_id, content_hash_sha256 FROM source_revision")
        ).fetchall()

    assert pending == [(url, "V0001-26")]
    assert queue_rows == [("V0001-26", url, "pending")]
    assert source_rows == []
```

- [ ] **Step 2: Add red integration assertions for `processed` and `empty` states**

```python
assert queue_row == (
    "processed",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2274-22",
)
assert re.fullmatch(r"[0-9a-f]{64}", revision_row[0])
assert source_revision_count == 0
assert empty_queue_row == (
    "empty",
    "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0001-26",
)
```

- [ ] **Step 3: Run only the new/changed DGT tests to verify red**

Run: `python -m pytest apps/workers/tests/test_dgt.py -q -k "queue_seed_entries_live_in_dgt_queue_not_source_revision or persists_target_dgt_document or skips_documents_outside_liva_and_lis"`

Expected: FAIL because DGT still writes queue state into `source_revision` and does not populate `dgt_queue`.

### Task 2: Implement runtime queue separation in `apps/workers/dgt.py`

**Files:**
- Modify: `apps/workers/dgt.py`
- Test: `apps/workers/tests/test_dgt.py`

- [ ] **Step 1: Add SQLite-only `dgt_queue` bootstrap helper**

```python
def ensure_dgt_queue_table(conn) -> None:
    dialect_name = conn.engine.dialect.name
    if dialect_name != "sqlite":
        return

    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS dgt_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_name TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                dgt_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                queued_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                processed_at TIMESTAMP,
                UNIQUE(worker_name, source_entity_id)
            )
            """
        )
    )
```

- [ ] **Step 2: Move queue helpers off `source_revision`**

```python
def _ensure_dgt_queue(conn, worker_name: str, seed_urls: list[str]) -> None:
    for url in seed_urls:
        num_consulta = _extract_num_consulta(url)
        conn.execute(
            text(
                """
                INSERT INTO dgt_queue (worker_name, source_entity_id, dgt_url, status)
                VALUES (:worker, :entity_id, :url, 'pending')
                ON CONFLICT (worker_name, source_entity_id) DO NOTHING
                """
            ),
            {"worker": worker_name, "entity_id": num_consulta, "url": url},
        )
```

- [ ] **Step 3: Update discovery and processing to use `dgt_queue`**

```python
existing_ids = set(
    row[0]
    for row in conn.execute(
        text(
            "SELECT source_entity_id FROM dgt_queue WHERE worker_name = :worker"
        ),
        {"worker": worker_name},
    ).fetchall()
)

_mark_done(conn, worker_name, entity_id, status="empty")
_mark_done(conn, worker_name, entity_id, status="processed")
```

- [ ] **Step 4: Re-run the focused DGT tests to verify green**

Run: `python -m pytest apps/workers/tests/test_dgt.py -q -k "queue_seed_entries_live_in_dgt_queue_not_source_revision or persists_target_dgt_document or skips_documents_outside_liva_and_lis"`

Expected: PASS.

### Task 3: Add Alembic migration and integrity coverage

**Files:**
- Create: `alembic/versions/20260504_0057_dgt_queue_split.py`
- Modify: `apps/api/tests/test_alembic_integrity.py`

- [ ] **Step 1: Create the migration with table, backfill, and sentinel cleanup**

```python
revision = "20260504_0057_dgt_queue_split"
down_revision = "20260504_0056_modelo_articulo_provenance"

op.execute(sa.text("CREATE TABLE IF NOT EXISTS dgt_queue (...)"))
op.execute(sa.text("INSERT INTO dgt_queue (...) SELECT ... FROM source_revision ..."))
op.execute(sa.text("DELETE FROM source_revision WHERE ... AND content_hash_sha256 !~ '^[0-9a-f]{64}$'"))
```

- [ ] **Step 2: Add a textual integrity test for revision `0057`**

```python
def test_dgt_queue_split_is_migrated_in_revision_0057():
    revision_path = ALEMBIC_VERSIONS / "20260504_0057_dgt_queue_split.py"
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "CREATE TABLE IF NOT EXISTS dgt_queue",
        "ADD CONSTRAINT ck_dgt_queue_status",
        "INSERT INTO dgt_queue",
        "FROM source_revision",
        "DELETE FROM source_revision",
        "content_hash_sha256 !~ '^[0-9a-f]{64}$'",
    ):
        assert fragment in contents
```

- [ ] **Step 3: Run integrity tests to verify green**

Run: `python -m pytest apps/api/tests/test_alembic_integrity.py -q`

Expected: PASS.

### Task 4: Verify the slice and update reusable docs

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`

- [ ] **Step 1: Run final slice verification**

Run: `python -m pytest apps/workers/tests/test_dgt.py -q`

Run: `python -m ruff check apps/workers/dgt.py apps/workers/tests/test_dgt.py alembic/versions/20260504_0057_dgt_queue_split.py apps/api/tests/test_alembic_integrity.py`

Expected: all green.

- [ ] **Step 2: Update roadmap live summary and historical note**

```markdown
- Estado actual: **Fase 4.1** `[COMPLETA]`
- Siguiente paso exacto: evaluar **Fase 4.2** ...
```

- [ ] **Step 3: Add one reusable agent note about DGT queue/revision separation**

```markdown
- Scope: `apps/workers/dgt.py`, `apps/workers/change_detection.py`
- Hallazgo: `source_revision` no puede compartir hash real y sentinels de cola sin romper el contrato de change detection.
- Impacto: una fila DGT `pending/empty` convierte una tabla compartida de revisiones en estado operativo ambiguo.
- Regla practica: toda cola persistente nueva debe vivir fuera de `source_revision`; esa tabla solo admite revisiones reales.
```
