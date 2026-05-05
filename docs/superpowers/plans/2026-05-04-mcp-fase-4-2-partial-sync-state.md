# MCP Fase 4.2 Partial Sync State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make worker sync logs report `partial` with a concrete message when AEAT/CNMV/DGT finish with missing resources or missing documents instead of overstating completion as `ok`.

**Architecture:** Add one tiny shared helper in `apps/workers/runtime.py` that derives final `status` and `error_msg` from a missing-artifact count and source label, then reuse it from `aeat_models.py`, `cnmv.py`, and `dgt.py`. Keep this slice sync-log only: no new tables, no per-item persistence, and no broader outcome framework.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest, Ruff

---

### Task 1: Add failing runtime helper tests

**Files:**
- Modify: `apps/workers/tests/test_runtime.py`
- Modify: `apps/workers/runtime.py`
- Reference: `docs/superpowers/specs/2026-05-04-mcp-fase-4-2-partial-sync-state-design.md`

- [ ] **Step 1: Write the failing runtime helper tests**

```python
def test_finalize_partial_sync_status_keeps_ok_without_missing_artifacts():
    status, error_msg = runtime.finalize_partial_sync_status(
        base_status="ok",
        missing_count=0,
        source_label="DGT documents",
    )

    assert status == "ok"
    assert error_msg is None


def test_finalize_partial_sync_status_degrades_ok_to_partial_with_message():
    status, error_msg = runtime.finalize_partial_sync_status(
        base_status="ok",
        missing_count=2,
        source_label="CNMV documents",
    )

    assert status == "partial"
    assert error_msg == "Skipped 2 CNMV documents after fetch failures"


def test_finalize_partial_sync_status_preserves_non_ok_base_status():
    status, error_msg = runtime.finalize_partial_sync_status(
        base_status="partial",
        missing_count=1,
        source_label="AEAT official resources",
    )

    assert status == "partial"
    assert error_msg == "Skipped 1 AEAT official resources after fetch failures"
```

- [ ] **Step 2: Run only the new runtime tests to verify red**

Run: `python -m pytest apps/workers/tests/test_runtime.py -q -k "finalize_partial_sync_status"`

Expected: FAIL with `AttributeError` because `runtime.finalize_partial_sync_status` does not exist yet.

- [ ] **Step 3: Implement the minimal runtime helper**

```python
def finalize_partial_sync_status(
    *,
    base_status: str,
    missing_count: int,
    source_label: str,
) -> tuple[str, str | None]:
    if missing_count <= 0:
        return base_status, None

    final_status = "partial" if base_status == "ok" else base_status
    return final_status, f"Skipped {missing_count} {source_label} after fetch failures"
```

- [ ] **Step 4: Run the runtime tests to verify green**

Run: `python -m pytest apps/workers/tests/test_runtime.py -q -k "finalize_partial_sync_status"`

Expected: PASS.

### Task 2: Refactor AEAT to use the shared helper without changing behavior

**Files:**
- Modify: `apps/workers/aeat_models.py:1019-1029`
- Test: `apps/workers/tests/test_aeat_models.py:1023-1092`
- Reference: `apps/workers/runtime.py`

- [ ] **Step 1: Keep the existing AEAT regression as the red/green guardrail**

Use existing regression:

```python
def test_run_sync_skips_failed_official_resource_and_finishes_partial(monkeypatch):
    ...
    assert row == ("partial", 0, "Skipped 1 AEAT official resources after fetch failures")
```

- [ ] **Step 2: Run the focused AEAT regression before the refactor**

Run: `python -m pytest apps/workers/tests/test_aeat_models.py -q -k "skips_failed_official_resource_and_finishes_partial"`

Expected: PASS before refactor, proving the current behavior we must preserve.

- [ ] **Step 3: Replace inline AEAT status/message construction with the helper**

```python
final_status, final_error_msg = finalize_partial_sync_status(
    base_status="ok" if stats["errores"] == 0 else "partial",
    missing_count=skipped_resource_failures,
    source_label="AEAT official resources",
)

_record_sync_log(
    conn,
    started_at,
    datetime.now(UTC),
    final_status,
    stats,
    final_error_msg,
)
```

- [ ] **Step 4: Re-run the focused AEAT regression to verify green**

Run: `python -m pytest apps/workers/tests/test_aeat_models.py -q -k "skips_failed_official_resource_and_finishes_partial"`

Expected: PASS with unchanged observable behavior.

### Task 3: Add failing CNMV partial-state regression and implement it

**Files:**
- Modify: `apps/workers/tests/test_cnmv.py`
- Modify: `apps/workers/cnmv.py`
- Reference: `apps/workers/tests/test_cnmv.py:419-516`

- [ ] **Step 1: Write the failing CNMV regression for one missing document**

```python
def test_run_sync_marks_partial_when_a_cnmv_document_fetch_fails(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE documento_interpretativo (...)"""))
        conn.execute(text("""CREATE TABLE sync_log (...)"""))

    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    monkeypatch.setattr("cnmv.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        "cnmv._discover_new_urls",
        lambda seed_urls=None: ["https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"],
    )

    result = run_sync(seed_urls=["https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"])

    with engine.begin() as conn:
        sync = conn.execute(
            text("SELECT status, documentos_processed, documentos_upserted, error_msg FROM sync_log ORDER BY id DESC LIMIT 1")
        ).fetchone()

    assert result == {"processed": 0, "stored": 0, "discovered": 1}
    assert sync == (
        "partial",
        0,
        0,
        "Skipped 1 CNMV documents after fetch failures",
    )
```

- [ ] **Step 2: Run the focused CNMV regression to verify red**

Run: `python -m pytest apps/workers/tests/test_cnmv.py -q -k "marks_partial_when_a_cnmv_document_fetch_fails"`

Expected: FAIL because `cnmv.run_sync()` still logs final status `ok` after swallowing the per-URL exception.

- [ ] **Step 3: Implement the minimal CNMV counter and helper usage**

```python
missing_document_failures = 0

for url in urls:
    try:
        ...
    except Exception:
        missing_document_failures += 1
        continue

final_status, final_error_msg = finalize_partial_sync_status(
    base_status="ok",
    missing_count=missing_document_failures,
    source_label="CNMV documents",
)

log_sync(
    conn,
    worker_name,
    final_status,
    documentos_processed=processed,
    documentos_upserted=stored,
    error_msg=final_error_msg,
)
```

- [ ] **Step 4: Run the focused CNMV tests to verify green**

Run: `python -m pytest apps/workers/tests/test_cnmv.py -q -k "marks_partial_when_a_cnmv_document_fetch_fails or persists_cnmv_document_and_metrics"`

Expected: PASS.

### Task 4: Add failing DGT partial-state regressions and implement them

**Files:**
- Modify: `apps/workers/tests/test_dgt.py`
- Modify: `apps/workers/dgt.py`
- Reference: `apps/workers/dgt.py:533-645`

- [ ] **Step 1: Write the failing DGT regression for missing search result**

```python
def test_run_sync_marks_partial_when_dgt_search_returns_no_results(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    original_client = httpx.Client

    with engine.begin() as conn:
        ensure_source_revision_table(conn)
        ensure_dgt_queue_table(conn)
        conn.execute(text("""CREATE TABLE sync_log (...)"""))
        _ensure_dgt_queue(
            conn,
            "worker-dgt",
            ["https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0001-26"],
        )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/consultas/":
            return httpx.Response(200, text="<html></html>", headers={"set-cookie": "JSESSIONID=abc123; Path=/consultas; HttpOnly"})
        if request.url.path == "/consultas/do/search":
            return httpx.Response(200, text='<div class="extra_padding"><div class="message">La consulta realizada no devuelve resultados.</div></div>')
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr("dgt.DGT_DISCOVERY", False)
    monkeypatch.setattr("dgt.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "dgt.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler), base_url="https://petete.tributos.hacienda.gob.es"),
    )
    monkeypatch.setattr("dgt.auto_link_doctrina", lambda conn: 0)

    result = run_sync(seed_urls=[])

    with engine.begin() as conn:
        sync_row = conn.execute(
            text("SELECT worker, status, documentos_processed, documentos_upserted, error_msg FROM sync_log ORDER BY id DESC LIMIT 1")
        ).fetchone()

    assert result == {"processed": 0, "stored": 0, "discovered": 0}
    assert sync_row == (
        "worker-dgt",
        "partial",
        0,
        0,
        "Skipped 1 DGT documents after fetch failures",
    )
```

- [ ] **Step 2: Write the DGT regression proving non-target docs stay non-partial**

Reuse the existing non-target fixture path and assert the sync log remains `ok` with no partial message.

```python
assert sync_row == ("worker-dgt", "ok", 1, 0, None)
```

- [ ] **Step 3: Run the focused DGT regressions to verify red**

Run: `python -m pytest apps/workers/tests/test_dgt.py -q -k "marks_partial_when_dgt_search_returns_no_results or skips_documents_outside_liva_and_lis"`

Expected: FAIL because `dgt.run_sync()` still logs final status `ok` when search results are missing.

- [ ] **Step 4: Implement the minimal DGT counter and helper usage**

```python
missing_document_failures = 0

if not results:
    missing_document_failures += 1
    with engine.begin() as conn:
        _mark_done(conn, worker_name, entity_id, "empty")
    continue

...

except Exception as e:
    missing_document_failures += 1
    logger.error("Error processing %s: %s", url, e)
    continue

final_status, final_error_msg = finalize_partial_sync_status(
    base_status="ok",
    missing_count=missing_document_failures,
    source_label="DGT documents",
)

log_sync(
    conn,
    worker_name,
    final_status,
    documentos_processed=total_processed,
    documentos_upserted=total_stored,
    doctrina_links_created=links_created,
    error_msg=final_error_msg,
)
```

- [ ] **Step 5: Run the focused DGT tests to verify green**

Run: `python -m pytest apps/workers/tests/test_dgt.py -q -k "marks_partial_when_dgt_search_returns_no_results or skips_documents_outside_liva_and_lis or persists_target_dgt_document"`

Expected: PASS.

### Task 5: Run final verification and update reusable docs

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`

- [ ] **Step 1: Run final slice verification**

Run: `python -m pytest apps/workers/tests/test_runtime.py apps/workers/tests/test_aeat_models.py apps/workers/tests/test_cnmv.py apps/workers/tests/test_dgt.py -q`

Run: `python -m ruff check apps/workers/runtime.py apps/workers/aeat_models.py apps/workers/cnmv.py apps/workers/dgt.py apps/workers/tests/test_runtime.py apps/workers/tests/test_aeat_models.py apps/workers/tests/test_cnmv.py apps/workers/tests/test_dgt.py`

Expected: all green.

- [ ] **Step 2: Update roadmap live summary and history**

```markdown
- Estado actual: **Fase 4.2** `[COMPLETA]`
- Siguiente paso exacto: abrir **Fase 4.3** ...
```

- [ ] **Step 3: Add one reusable agent note about sync-log `partial` semantics**

```markdown
- Scope: `apps/workers/runtime.py`, `apps/workers/cnmv.py`, `apps/workers/dgt.py`, `apps/workers/aeat_models.py`
- Hallazgo: un worker puede terminar sin excepcion global y aun asi no haber completado el corpus esperado.
- Impacto: cerrar `ok` en ese caso hace que el `sync_log` sobrestime completitud y esconda huecos reales de retrieval/fetch.
- Regla practica: si un run termina con artefactos faltantes pero sin error terminal, registrar `partial` con contador y fuente explicita; reservar `ok` para runs sin huecos materiales.
```
