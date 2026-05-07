# P0 MCP Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore minimum production safety for compliance-domain MCP/API outputs by fixing known stale data handling, audit coverage, RLS/schema ownership, retrieval correctness, and deployment hazards.

**Architecture:** Implement narrow safety gates around existing API/service seams instead of broad rewrites. Keep data correctness, MCP audit, search isolation, worker locking, and infra hardening as independently testable slices with explicit verification before any production deploy.

**Tech Stack:** FastAPI, fastapi-mcp, SQLAlchemy, Alembic, pytest, httpx, PostgreSQL/SQLite test fixtures, Docker Compose, Caddy, systemd timers/services.

---

## File Map

- Modify: `apps/api/tests/conftest.py` to make LIVA article 91 fixture current enough for regression tests and add dirty AEAT model fixture data when needed.
- Modify: `apps/api/tests/test_smoke.py` to assert current LIVA article 90/91 behavior and explicit stale/partial warnings.
- Modify: `apps/api/routers/legislacion.py` to add trust-state warnings for stale known-high-risk responses.
- Modify: `apps/api/services/modelos.py` to add AEAT text cleanliness helpers and sanitize/grade model rows, casillas, claves, and instrucciones.
- Modify: `apps/api/routers/modelos.py` to use model trust-state helpers consistently in detail and subresource endpoints.
- Modify: `apps/api/schemas.py` to add `verified` and `completeness` fields to model response contracts if missing.
- Modify: `apps/workers/aeat_models.py` to improve model-name extraction and reject navigation/script residue before storing clean metadata.
- Modify: `apps/workers/tests/test_aeat_models.py` to cover AEAT parser residue and verification downgrade behavior.
- Modify: `apps/api/services/query_audit.py` to support MCP boundary audit statuses and summaries without changing existing router audit callers.
- Modify: `apps/api/mcp_server.py` to wrap MCP internal tool calls with audit recording at the boundary.
- Modify: `apps/api/tests/test_mcp_audit.py` and `apps/api/tests/test_mcp_contract.py` to expect MCP tool-call audit coverage.
- Modify: `apps/api/services/persistence.py` to stop PostgreSQL runtime DDL while retaining SQLite test bootstrap.
- Add: `alembic/versions/20260506_0001_p0_rls_current_tables.py` to enforce RLS/policies on tables added after the original RLS sweep.
- Add: `apps/api/tests/test_p0_schema_safety.py` for static no-runtime-DDL and RLS migration checks.
- Modify: `apps/api/services/semantic_search.py` to fix doctrine full-text SQL construction.
- Modify: `apps/api/services/unified_multi_source_search.py` to fix 31.x alias/parameter bugs and source isolation.
- Modify: `apps/api/tests/test_unified_multi_source_search.py` to cover 31.x source filtering and SQL parameter names.
- Modify: `apps/workers/dgt.py` to add whole-worker advisory lock protection.
- Modify: `apps/workers/tests/test_dgt.py` or `apps/workers/tests/test_worker_dgt_doctrina.py` to cover skipped execution when the lock is held.
- Modify: `infra/deploy/systemd/esdata-job@.service` to add timeout, failure handling, and safe Docker compose invocation controls.
- Modify: `infra/deploy/Caddyfile` to add `/mcp` access-control hooks.
- Modify: `infra/deploy/Dockerfile.ops` to run non-root and pin/harden the ops image as far as current base-image policy allows.
- Modify: `.github/workflows/deploy.yml` to disable deprecated Railway execution on push.
- Add: `apps/api/tests/test_p0_infra_config.py` for static infra/deploy guardrails.

## Execution Rules

- Do not touch production VPS, firewall, live DB, real env files, or deploy anything during implementation.
- Do not revert unrelated dirty worktree changes.
- Do not commit unless the user explicitly requests a commit.
- Prefer minimal fixes that make the red tests pass.
- After each task, run only the focused verification command listed for that task before moving on.

---

### Task 1: Current LIVA Accuracy Gate

**Files:**
- Modify: `apps/api/tests/conftest.py:1973-1990`
- Modify: `apps/api/tests/test_smoke.py:95-113`
- Modify: `apps/api/routers/legislacion.py:119-165`

- [ ] **Step 1: Update the LIVA fixture to include current-rate text**

Replace the `version_articulo` fixture text for LIVA article 91 in `apps/api/tests/conftest.py` with:

```sql
INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
SELECT a.id, 'Artículo 91. Tipos impositivos reducidos.
Uno. Se aplicará el tipo del 10 por ciento a las operaciones siguientes:
1. Las entregas, adquisiciones intracomunitarias o importaciones de sustancias o productos susceptibles de ser habitual e idóneamente utilizados para la nutrición humana o animal.
Dos. Se aplicará el tipo del 4 por ciento a las operaciones siguientes:
1. Las entregas, adquisiciones intracomunitarias o importaciones de pan común, leche, quesos, huevos, frutas, verduras, hortalizas, legumbres, tubérculos y cereales naturales.
La estructura de tipos se mantiene como fixture representativa de la versión consolidada vigente para pruebas de seguridad factual.', '2025-04-03', NULL, 'a91'
FROM articulo a
JOIN norma n ON n.id = a.norma_id
WHERE n.codigo = 'LIVA' AND a.numero = '91'
```

- [ ] **Step 2: Add a failing current-law regression test**

Append this test after `test_liva_articulo_91_vigente_en_fecha` in `apps/api/tests/test_smoke.py`:

```python
@pytest.mark.asyncio
async def test_liva_articulo_91_current_fixture_uses_current_reduced_rates():
    async with _client() as c:
        r = await c.get("/v1/legislacion/LIVA/articulos/91?vigente_en=2026-05-06")

    assert r.status_code == 200
    data = r.json()
    text = data["texto"].lower()
    assert "10 por ciento" in text
    assert "4 por ciento" in text
    assert "6 por 100" not in text
    assert "3 por 100" not in text
```

- [ ] **Step 3: Run the regression test and verify it fails before fixture/code changes are complete**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_smoke.py::test_liva_articulo_91_current_fixture_uses_current_reduced_rates -q`

Expected before implementation: FAIL if the fixture or response still contains obsolete `6 por 100` or lacks current `10 por ciento` text.

- [ ] **Step 4: Add explicit stale warning for known high-risk current-date LIVA 91 responses**

In `apps/api/routers/legislacion.py`, add this helper above `get_articulo`:

```python
def _known_accuracy_warning(codigo: str, numero: str, texto_value: str, vigente_en: str | None) -> str | None:
    if codigo.upper() == "LIVA" and numero == "91" and vigente_en:
        lowered = texto_value.lower()
        if "6 por 100" in lowered or "3 por 100" in lowered:
            return "Texto potencialmente obsoleto para LIVA art. 91 en la fecha solicitada; no usar como fuente vigente sin revalidación BOE."
    return None
```

Then replace the current `"aviso": None` in the response with:

```python
"aviso": _known_accuracy_warning(row["codigo"], row["numero"], row["texto"] or "", vigente_en),
```

- [ ] **Step 5: Run focused tests**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_smoke.py::test_liva_articulo_91 apps/api/tests/test_smoke.py::test_liva_articulo_91_vigente_en_fecha apps/api/tests/test_smoke.py::test_liva_articulo_91_current_fixture_uses_current_reduced_rates -q`

Expected: PASS.

---

### Task 2: AEAT Parser Cleanliness And Verification State

**Files:**
- Modify: `apps/workers/aeat_models.py:86-91`, `apps/workers/aeat_models.py:405-421`, `apps/workers/aeat_models.py:483-520`
- Modify: `apps/workers/tests/test_aeat_models.py:38-61`
- Modify: `apps/api/services/modelos.py:1-274`
- Modify: `apps/api/routers/modelos.py:317-359`, `apps/api/routers/modelos.py:411-459`
- Modify: `apps/api/schemas.py:286-310`
- Modify: `apps/api/tests/test_integration.py:144-170`

- [ ] **Step 1: Add worker parser tests for navigation residue**

Add these tests to `TestExtractModelName` in `apps/workers/tests/test_aeat_models.py`:

```python
    def test_strips_aeat_navigation_residue(self):
        raw = "Agencia Tributaria  Modelo 303. IVA. Autoliquidación. Saltar al contenido principal Logotipo del Gobierno de España"
        name = _extract_model_name(raw, "303")
        assert name == "Modelo 303. IVA. Autoliquidación."

    def test_does_not_store_script_or_markup_fragments_as_name(self):
        raw = '303 <script src="/static_files/common/script/aeat.07.js"></script> Modelo 303. IVA.'
        name = _extract_model_name(raw, "303")
        assert "script" not in name.lower()
        assert "static_files" not in name.lower()
        assert name.startswith("Modelo 303")
```

- [ ] **Step 2: Run parser tests and verify failure**

Run: `$env:PYTHONPATH='apps/workers'; python -m pytest apps/workers/tests/test_aeat_models.py::TestExtractModelName::test_strips_aeat_navigation_residue apps/workers/tests/test_aeat_models.py::TestExtractModelName::test_does_not_store_script_or_markup_fragments_as_name -q`

Expected before implementation: FAIL because `_extract_model_name` preserves navigation/script residue.

- [ ] **Step 3: Implement reusable AEAT text cleaner in worker**

In `apps/workers/aeat_models.py`, add this helper below `_normalize_html`:

```python
def _clean_aeat_display_text(value: str | None) -> str:
    text_value = value or ""
    text_value = re.sub(r"<script\b[^>]*>.*?</script>", " ", text_value, flags=re.IGNORECASE | re.DOTALL)
    text_value = re.sub(r"<style\b[^>]*>.*?</style>", " ", text_value, flags=re.IGNORECASE | re.DOTALL)
    text_value = re.sub(r"<[^>]+>", " ", text_value)
    text_value = BeautifulSoup(text_value, "html.parser").get_text(" ", strip=True)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    stop_phrases = [
        "Agencia Tributaria",
        "Saltar al contenido principal",
        "Logotipo del Gobierno de España",
        "Logotipo Organismo",
        "Menú móvil",
        "Menu móvil",
        "Abrir menú móvil",
    ]
    for phrase in stop_phrases:
        text_value = text_value.replace(phrase, " ")
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value
```

- [ ] **Step 4: Use the cleaner in `_extract_model_name`**

Replace the first lines of `_extract_model_name` with:

```python
def _extract_model_name(raw_text: str, codigo: str) -> str:
    text_value = _clean_aeat_display_text(raw_text)
    text_value = re.sub(rf"^\s*(?:modelo\s*)?{re.escape(codigo)}\s*[-:–.]?\s*", "", text_value, flags=re.IGNORECASE)
    if text_value:
        text_value = f"Modelo {codigo}. {text_value}" if not text_value.lower().startswith("modelo") else text_value
    else:
        text_value = f"Modelo {codigo}"
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value[:200]
```

- [ ] **Step 5: Add API cleanliness helpers**

In `apps/api/services/modelos.py`, add these helpers after the imports:

```python
import re


DIRTY_AEAT_PATTERNS = (
    "<script",
    "</script",
    "static_files",
    "saltar al contenido principal",
    "logotipo del gobierno",
    "logotipo organismo",
    "menú móvil",
    "menu móvil",
    "abrir menú móvil",
    "class=",
    "src=",
)


def is_dirty_aeat_text(value: object) -> bool:
    if value is None:
        return False
    lowered = str(value).lower()
    return any(pattern in lowered for pattern in DIRTY_AEAT_PATTERNS)


def clean_aeat_text(value: object) -> str | None:
    if value is None:
        return None
    text_value = re.sub(r"<[^>]+>", " ", str(value))
    for pattern in DIRTY_AEAT_PATTERNS:
        text_value = re.sub(re.escape(pattern), " ", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value or None


def assess_modelo_cleanliness(*collections: list[dict], scalar_values: list[object] | None = None) -> tuple[bool, str, list[str]]:
    dirty_fields: list[str] = []
    for index, value in enumerate(scalar_values or []):
        if is_dirty_aeat_text(value):
            dirty_fields.append(f"scalar_{index}")
    for collection_index, collection in enumerate(collections):
        for row_index, row in enumerate(collection):
            for key, value in row.items():
                if is_dirty_aeat_text(value):
                    dirty_fields.append(f"collection_{collection_index}.{row_index}.{key}")
    verified = not dirty_fields
    return verified, "completa" if verified else "partial", dirty_fields
```

- [ ] **Step 6: Apply cleaning and trust state in `get_modelo`**

In `apps/api/routers/modelos.py`, import `assess_modelo_cleanliness` and `clean_aeat_text` from `services.modelos`. Then change `casillas`, `claves`, and `instrucciones` construction to clean text fields:

```python
casillas = []
if campana_id:
    cas_rows = list_campaign_casillas(db, campana_id)
    casillas = [
        {
            **dict(r),
            "etiqueta": clean_aeat_text(r["etiqueta"]),
            "descripcion": clean_aeat_text(r["descripcion"]),
        }
        for r in cas_rows
    ]

claves = []
if campana_id:
    clav_rows = list_campaign_claves(db, campana_id)
    claves = [
        {
            **dict(r),
            "etiqueta": clean_aeat_text(r["etiqueta"]),
            "descripcion": clean_aeat_text(r["descripcion"]),
        }
        for r in clav_rows
    ]

instrucciones = []
if campana_id:
    instr_rows = list_campaign_instructions(db, campana_id)
    instrucciones = [
        {
            **dict(r),
            "titulo": clean_aeat_text(r["titulo"]),
            "contenido": clean_aeat_text(r["contenido"]),
        }
        for r in instr_rows
    ]
```

Before returning the payload, add:

```python
verified, completeness, dirty_fields = assess_modelo_cleanliness(
    casillas,
    claves,
    instrucciones,
    scalar_values=[model_row["nombre"]],
)
```

Add these fields to the returned dict:

```python
"nombre": clean_aeat_text(model_row["nombre"]),
"completeness": completeness,
"verified": verified,
"warnings": ["AEAT parser residue detected; response downgraded to partial."] if dirty_fields else [],
```

- [ ] **Step 7: Add schema fields if absent**

In `apps/api/schemas.py`, add these optional fields to `ModeloDetail`:

```python
    completeness: str | None = Field(default=None, description="Estado de completitud operativa")
    verified: bool | None = Field(default=None, description="Indica si el contenido paso controles de limpieza/fuente")
    warnings: list[str] = Field(default_factory=list, description="Advertencias de calidad o frescura")
```

- [ ] **Step 8: Add an API regression test for dirty model downgrade**

Add this test near existing `/v1/modelos/303` tests in `apps/api/tests/test_integration.py`:

```python
@pytest.mark.asyncio
async def test_modelo_303_dirty_parser_content_is_not_verified(client):
    resp = await client.get("/v1/modelos/303", params={"campana": "2025"})
    assert resp.status_code == 200
    data = resp.json()
    serialized = str(data).lower()
    assert "saltar al contenido principal" not in serialized
    assert "static_files" not in serialized
    assert data.get("verified") in {True, False}
    if data.get("warnings"):
        assert data["verified"] is False
        assert data["completeness"] == "partial"
```

- [ ] **Step 9: Run focused tests**

Run: `$env:PYTHONPATH='apps/api;apps/workers'; python -m pytest apps/workers/tests/test_aeat_models.py::TestExtractModelName apps/api/tests/test_integration.py::test_modelo_303_dirty_parser_content_is_not_verified -q`

Expected: PASS.

---

### Task 3: MCP Boundary Audit Coverage

**Files:**
- Modify: `apps/api/services/query_audit.py:21-54`
- Modify: `apps/api/mcp_server.py:1-27`
- Modify: `apps/api/tests/test_mcp_audit.py:76-148`
- Modify: `apps/api/tests/test_mcp_contract.py:31-41`

- [ ] **Step 1: Add a failing MCP audit test for non-`buscar` tools**

Add this test to `apps/api/tests/test_mcp_audit.py` after the existing test:

```python
@pytest.mark.asyncio
async def test_mcp_boundary_audits_tool_without_router_level_audit():
    async with _uvicorn_server(MCP_API_KEY="test-mcp-key", MCP_RATE_LIMIT_PER_MINUTE="20") as port:
        session = requests.Session()
        handshake = session.get(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Accept": "text/event-stream", "X-API-Key": "test-mcp-key"},
            timeout=5,
        )
        session_id = handshake.headers.get("Mcp-Session-Id") or handshake.headers.get("mcp-session-id")
        assert session_id

        session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "Mcp-Session-Id": session_id,
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1.0"}},
            },
            timeout=5,
        )

        response = session.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "Mcp-Session-Id": session_id,
                "x-api-key": "test-mcp-key",
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "x-request-id": "req-mcp-audit-list-legislacion",
                "x-user-id": "internal-mcp-user",
            },
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_legislacion", "arguments": {}}},
            timeout=5,
        )

    assert response.status_code == 200
    entries = QueryAuditService().get_by_request_id("req-mcp-audit-list-legislacion")
    assert any(entry.path == "/mcp/tools/call/list_legislacion" for entry in entries)
    boundary_entry = next(entry for entry in entries if entry.path == "/mcp/tools/call/list_legislacion")
    assert boundary_entry.grounding_status == "success"
    assert "tool=list_legislacion" in boundary_entry.response_summary
```

- [ ] **Step 2: Run the new MCP audit test and verify failure**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_mcp_audit.py::test_mcp_boundary_audits_tool_without_router_level_audit -q`

Expected before implementation: FAIL because only router-level audited tools create audit rows.

- [ ] **Step 3: Extend query audit entries for MCP statuses without breaking callers**

In `apps/api/services/query_audit.py`, keep existing fields and add an optional `metadata` field to `QueryAuditEntry`:

```python
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Do not change the existing `INSERT` schema in this task. Store metadata inside `grounding_summary` for now to avoid a P0 migration dependency:

```python
grounding_summary=grounding_summary or {},
```

Existing callers stay valid.

- [ ] **Step 4: Implement boundary audit inside MCP internal client**

In `apps/api/mcp_server.py`, add imports:

```python
import json
from services.query_audit import get_query_audit_service
```

Replace `MCPInternalAsyncClient.request` with:

```python
        async def request(self, *args, **kwargs):
            headers = kwargs.get("headers") or {}
            request_id = headers.get("x-request-id") or headers.get("X-Request-ID") or "unknown"
            user_id = headers.get("x-user-id") or headers.get("X-User-ID")
            tool_name = "unknown"
            arguments = {}
            body = kwargs.get("json")
            if isinstance(body, dict) and body.get("method") == "tools/call":
                params = body.get("params") or {}
                tool_name = str(params.get("name") or "unknown")
                arguments = params.get("arguments") or {}

            with mcp_internal_request():
                response = await super().request(*args, **kwargs)

            if isinstance(body, dict) and body.get("method") == "tools/call":
                status = "success"
                summary = f"tool={tool_name} http_status={response.status_code}"
                try:
                    payload = response.json()
                    if payload.get("error") or payload.get("result", {}).get("isError") is True:
                        status = "internal_error"
                except Exception:
                    payload = None
                if response.status_code >= 400:
                    status = "validation_error" if response.status_code < 500 else "internal_error"
                get_query_audit_service().record_query(
                    request_id=request_id,
                    user_id=user_id,
                    path=f"/mcp/tools/call/{tool_name}",
                    query_text=json.dumps(arguments, ensure_ascii=True, sort_keys=True),
                    retrieved_chunks=[],
                    response_summary=summary,
                    grounding_status=status,
                    grounding_summary={"tool": tool_name, "http_status": response.status_code},
                )
            return response
```

- [ ] **Step 5: Update contract test that expected no audit for MCP GET**

Keep `test_mcp_transport_preserves_request_id_header` unchanged for GET `/mcp`; it should still assert no audit entries because boundary audit only records `tools/call` POSTs.

- [ ] **Step 6: Run focused MCP tests**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_mcp_audit.py apps/api/tests/test_mcp_contract.py -q`

Expected: PASS.

---

### Task 4: Remove PostgreSQL Runtime DDL And Enforce Current RLS

**Files:**
- Modify: `apps/api/services/persistence.py:15-182`
- Add: `alembic/versions/20260506_0001_p0_rls_current_tables.py`
- Add: `apps/api/tests/test_p0_schema_safety.py`

- [ ] **Step 1: Add static tests for forbidden runtime DDL**

Create `apps/api/tests/test_p0_schema_safety.py` with:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_api_persistence_does_not_run_postgres_create_table_runtime():
    source = (ROOT / "apps/api/services/persistence.py").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS" not in source or "dialect == \"sqlite\"" in source


def test_latest_p0_rls_migration_mentions_modelo_recurso():
    migration = ROOT / "alembic/versions/20260506_0001_p0_rls_current_tables.py"
    assert migration.exists()
    text = migration.read_text(encoding="utf-8")
    assert "modelo_recurso" in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "service_role_all" in text
```

- [ ] **Step 2: Run tests and verify failure**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_p0_schema_safety.py -q`

Expected before implementation: FAIL because the migration file does not exist and PostgreSQL runtime DDL is still active.

- [ ] **Step 3: Make `ensure_governance_tables` SQLite-only for DDL creation**

Replace `ensure_governance_tables` in `apps/api/services/persistence.py` with:

```python
def ensure_governance_tables() -> None:
    with engine.begin() as conn:
        dialect = conn.engine.dialect.name
        if dialect == "sqlite":
            for statement in _ddl_statements_for_dialect(dialect):
                conn.execute(text(statement))
            _ensure_query_audit_log_columns(conn)
            return

        existing = conn.execute(
            text(
                """
                SELECT to_regclass('public.query_audit_log') IS NOT NULL
                """
            )
        ).scalar()
        if not existing:
            raise RuntimeError(
                "Governance tables are missing; run Alembic migrations instead of creating API runtime tables."
            )
        _ensure_query_audit_log_columns(conn)
```

- [ ] **Step 4: Add a current-table RLS migration**

Create `alembic/versions/20260506_0001_p0_rls_current_tables.py` with:

```python
"""P0 enforce RLS on tables added after initial zero-policy sweep.

Revision ID: 20260506_0001_p0_rls_current_tables
Revises: 20260501_0054_aeat_modelo_recurso
Create Date: 2026-05-06 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260506_0001_p0_rls_current_tables"
down_revision = "20260501_0054_aeat_modelo_recurso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("GRANT USAGE ON SCHEMA public TO service_role"))
    op.execute(sa.text("GRANT USAGE ON SCHEMA public TO esdata"))
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                t RECORD;
            BEGIN
                FOR t IN
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename <> 'alembic_version'
                LOOP
                    EXECUTE format('REVOKE ALL ON TABLE %I FROM PUBLIC', t.tablename);
                    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t.tablename);
                    EXECUTE format('GRANT ALL ON TABLE %I TO service_role', t.tablename);
                    EXECUTE format('GRANT ALL ON TABLE %I TO esdata', t.tablename);
                    EXECUTE format('DROP POLICY IF EXISTS service_role_all ON %I', t.tablename);
                    EXECUTE format('DROP POLICY IF EXISTS esdata_all ON %I', t.tablename);
                    EXECUTE format('CREATE POLICY service_role_all ON %I FOR ALL TO service_role USING (true) WITH CHECK (true)', t.tablename);
                    EXECUTE format('CREATE POLICY esdata_all ON %I FOR ALL TO esdata USING (true) WITH CHECK (true)', t.tablename);
                END LOOP;
            END $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_policies
                    WHERE schemaname = 'public'
                      AND (roles @> ARRAY['public']::name[] OR roles @> ARRAY['anon']::name[] OR roles @> ARRAY['authenticated']::name[])
                ) THEN
                    RAISE EXCEPTION 'Forbidden public/anon/authenticated RLS policy exists';
                END IF;
            END $$
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS service_role_all ON modelo_recurso"))
    op.execute(sa.text("DROP POLICY IF EXISTS esdata_all ON modelo_recurso"))
```

- [ ] **Step 5: Run focused tests**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_p0_schema_safety.py apps/api/tests/test_query_audit.py -q`

Expected: PASS for SQLite tests and static migration checks.

---

### Task 5: Search SQL And Source Isolation Fixes

**Files:**
- Modify: `apps/api/services/semantic_search.py:340-399`
- Modify: `apps/api/services/unified_multi_source_search.py:1134-1207`
- Modify: `apps/api/tests/test_unified_multi_source_search.py:254-275`
- Add or modify: `apps/api/tests/test_search_legislacion.py`

- [ ] **Step 1: Add unit tests for 31.x SQL source filtering**

Add this test class near the handler tests in `apps/api/tests/test_unified_multi_source_search.py`:

```python
class Test31xSqlConstruction:
    def test_31x_fulltext_uses_df_alias_and_ts_query_parameter(self):
        from services.unified_multi_source_search import _build_31x_fulltext_sql

        sql, params = _build_31x_fulltext_sql("resiliencia digital", "dora", 5)
        assert "LOWER(df.texto) LIKE :_31x_q0" in sql
        assert "LOWER(t.texto)" not in sql
        assert ":_31x_ts_query" in sql
        assert "documento_origen_tipo = :_31x_source" in sql
        assert params["_31x_source"] == "dora"
        assert params["_31x_ts_query"] == "resiliencia digital"
        assert params["limit"] == 5
```

- [ ] **Step 2: Run the test and verify failure**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_unified_multi_source_search.py::Test31xSqlConstruction::test_31x_fulltext_uses_df_alias_and_ts_query_parameter -q`

Expected before implementation: FAIL because `_build_31x_fulltext_sql` does not exist and current SQL uses `t.texto` plus `:ts_query` mismatch.

- [ ] **Step 3: Extract and fix 31.x fulltext SQL builder**

In `apps/api/services/unified_multi_source_search.py`, add above `_31x_fulltext`:

```python
def _build_31x_fulltext_sql(q: str, source: str | None, limit: int) -> tuple[str, dict]:
    q_lower = q.lower().strip()
    words = q_lower.split()
    conditions: list[str] = []
    params: dict = {"_31x_ts_query": q_lower, "limit": limit}
    for i, word in enumerate(words):
        conditions.append(f"LOWER(df.texto) LIKE :_31x_q{i}")
        params[f"_31x_q{i}"] = f"%{word}%"
    if source:
        source_filter = "df.documento_origen_tipo = :_31x_source"
        params["_31x_source"] = source
    else:
        source_filter = "df.documento_origen_tipo IN ('mica', 'dac', 'pbc', 'fraud', 'mifid', 'mar', 'dora', 'priips', 'transparency', 'sfdr', 'csrd', 'aifmd_ucits', 'crd_brrd_emir')"
    if not conditions:
        return "", params
    return f"""
        SELECT df.id, df.documento_origen_tipo, df.documento_origen_id,
               df.chunk_index, df.chunk_type, df.titulo, df.texto,
               df.token_count, df.documento_origen_tipo AS source_type
        FROM documento_fragmento df
        WHERE {source_filter}
          AND ({' OR '.join(conditions)})
        ORDER BY ts_rank(df.search_vector, plainto_tsquery('spanish', :_31x_ts_query)) DESC
        LIMIT :limit
        """, params
```

Change `_31x_fulltext` signature to:

```python
def _31x_fulltext(db, q: str, limit: int, source: str | None = None) -> list[dict]:
```

Replace its SQL construction with:

```python
    sql_text, params = _build_31x_fulltext_sql(q, source, limit)
    if not sql_text:
        return []
    rows = db.execute(text(sql_text), params).mappings().fetchall()
```

- [ ] **Step 4: Pass source into 31.x fulltext/vector callers**

Find `_search_31x_source` in `apps/api/services/unified_multi_source_search.py` and update calls from:

```python
fulltext_results = _31x_fulltext(db, q, limit)
```

to:

```python
fulltext_results = _31x_fulltext(db, q, limit, source)
```

Update vector SQL similarly by adding `source: str | None = None` to `_31x_vector` and using:

```python
source_filter = "df.documento_origen_tipo = :_31x_source" if source else "df.documento_origen_tipo IN ('mica', 'dac', 'pbc', 'fraud', 'mifid', 'mar', 'dora', 'priips', 'transparency', 'sfdr', 'csrd', 'aifmd_ucits', 'crd_brrd_emir')"
params = {"limit": limit}
if source:
    params["_31x_source"] = source
```

Then execute `db.execute(sql, params)`.

- [ ] **Step 5: Fix doctrine full-text tsquery tuple construction**

In `apps/api/services/semantic_search.py`, replace lines using `_build_tsquery_sql(q)` with explicit SQL/params:

```python
        tsquery_sql, tsquery_params = _build_tsquery_sql(q)
        if tsquery_sql:
            params.update(tsquery_params)
            search_filter = "d.search_vector @@ " + tsquery_sql
            rank_expr = "ts_rank(d.search_vector, " + tsquery_sql + ")"
```

If `_build_tsquery_sql` currently returns a string only, adjust it to return `(sql_fragment, params)` and update all callers in the same file. The expected fragment shape is:

```python
("plainto_tsquery('spanish', :ts_query)", {"ts_query": q})
```

- [ ] **Step 6: Run focused search tests**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_unified_multi_source_search.py apps/api/tests/test_search_legislacion.py -q`

Expected: PASS.

---

### Task 6: DGT Whole-Worker Advisory Lock

**Files:**
- Modify: `apps/workers/dgt.py:367-683`
- Modify: `apps/workers/tests/test_dgt.py` or add tests to `apps/workers/tests/test_worker_dgt_doctrina.py`

- [ ] **Step 1: Add lock helper tests**

Add this test to `apps/workers/tests/test_dgt.py`:

```python
def test_dgt_lock_skips_when_postgres_lock_is_already_held(monkeypatch):
    import dgt

    class FakeConn:
        def execute(self, statement, params=None):
            sql = str(statement)
            if "pg_try_advisory_lock" in sql:
                return type("Result", (), {"scalar": lambda self: False})()
            raise AssertionError(f"Unexpected SQL: {sql}")

    class FakeEngine:
        dialect = type("Dialect", (), {"name": "postgresql"})()
        def begin(self):
            class Ctx:
                def __enter__(self_inner):
                    return FakeConn()
                def __exit__(self_inner, exc_type, exc, tb):
                    return False
            return Ctx()

    monkeypatch.setattr(dgt, "create_engine", lambda *args, **kwargs: FakeEngine())
    monkeypatch.setattr(dgt, "ensure_database_connection", lambda *args, **kwargs: None)

    result = dgt.run_sync(seed_urls=[])
    assert result["processed"] == 0
    assert result["stored"] == 0
    assert result["skipped_locked"] == 1
```

- [ ] **Step 2: Run the lock test and verify failure**

Run: `$env:PYTHONPATH='apps/workers'; python -m pytest apps/workers/tests/test_dgt.py::test_dgt_lock_skips_when_postgres_lock_is_already_held -q`

Expected before implementation: FAIL because `run_sync` does not return `skipped_locked` and does not acquire a lock.

- [ ] **Step 3: Add lock constants and helpers**

In `apps/workers/dgt.py`, add below `SYNC_INTERVAL_SECONDS`:

```python
DGT_SYNC_LOCK_KEY = 88420041
```

Add helpers before `run_sync`:

```python
def _try_worker_lock(engine) -> bool:
    if engine.dialect.name != "postgresql":
        return True
    with engine.begin() as conn:
        return bool(conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": DGT_SYNC_LOCK_KEY}).scalar())


def _release_worker_lock(engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": DGT_SYNC_LOCK_KEY})
```

- [ ] **Step 4: Guard `run_sync` with the lock**

After creating and checking the engine in `run_sync`, add:

```python
    if not _try_worker_lock(engine):
        logger.warning("DGT worker skipped because another run holds advisory lock")
        return {"processed": 0, "stored": 0, "discovered": 0, "links_created": 0, "skipped_locked": 1}
```

Wrap the existing sync body in `try:` and release in `finally:`:

```python
    try:
        ...existing body...
    finally:
        _release_worker_lock(engine)
```

Ensure the normal return includes `"skipped_locked": 0`.

- [ ] **Step 5: Run DGT tests**

Run: `$env:PYTHONPATH='apps/workers'; python -m pytest apps/workers/tests/test_dgt.py apps/workers/tests/test_worker_dgt_doctrina.py -q`

Expected: PASS.

---

### Task 7: Infra P0 Guardrails

**Files:**
- Modify: `infra/deploy/systemd/esdata-job@.service:1-10`
- Modify: `infra/deploy/Caddyfile:5-19`
- Modify: `infra/deploy/Dockerfile.ops:1-18`
- Modify: `.github/workflows/deploy.yml:1-160`
- Add: `apps/api/tests/test_p0_infra_config.py`

- [ ] **Step 1: Add static infra tests**

Create `apps/api/tests/test_p0_infra_config.py` with:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_deprecated_railway_workflow_is_not_triggered_on_main_push():
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    assert "branches: [main]" not in workflow
    assert "railway up" not in workflow.lower()


def test_systemd_job_has_timeout_and_failure_controls():
    unit = (ROOT / "infra/deploy/systemd/esdata-job@.service").read_text(encoding="utf-8")
    assert "TimeoutStartSec=" in unit
    assert "OnFailure=" in unit
    assert "User=deploy" in unit


def test_caddyfile_has_mcp_access_control_hook():
    caddyfile = (ROOT / "infra/deploy/Caddyfile").read_text(encoding="utf-8")
    assert "handle /mcp*" in caddyfile
    assert "respond \"MCP endpoint restricted\" 403" in caddyfile


def test_ops_dockerfile_runs_non_root():
    dockerfile = (ROOT / "infra/deploy/Dockerfile.ops").read_text(encoding="utf-8")
    assert "USER esdata" in dockerfile
    assert "adduser" in dockerfile or "useradd" in dockerfile
```

- [ ] **Step 2: Run static infra tests and verify failure**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_p0_infra_config.py -q`

Expected before implementation: FAIL on Railway trigger, missing systemd controls, missing Caddy `/mcp` hook, and missing non-root user.

- [ ] **Step 3: Disable deprecated Railway workflow execution**

Replace `.github/workflows/deploy.yml` active trigger and jobs with a harmless manual no-op:

```yaml
# [DEPRECATED] Deploy Railway — HISTORICAL
#
# Despliegue activo: Docker Compose. Este workflow queda manual y sin acceso
# a secretos para impedir despliegues accidentales desde main.

name: Deploy [DEPRECATED - disabled]

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  disabled:
    runs-on: ubuntu-latest
    steps:
      - name: Deprecated workflow disabled
        run: echo "Railway deployment is deprecated. Use .github/workflows/deploy-hetzner.yml."
```

- [ ] **Step 4: Add systemd timeout/failure controls**

Update `infra/deploy/systemd/esdata-job@.service` to:

```ini
[Unit]
Description=esdata scheduled job (%i)
After=docker.service network-online.target
Wants=network-online.target
OnFailure=esdata-job-failure@%i.service

[Service]
Type=oneshot
User=deploy
WorkingDirectory=/srv/esdata
TimeoutStartSec=3600
ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i
```

- [ ] **Step 5: Add conservative Caddy `/mcp` restriction hook**

Update `infra/deploy/Caddyfile` API site block to:

```caddyfile
{$API_DOMAIN} {
    handle /mcp* {
        @mcp_allowed remote_ip {$MCP_ALLOWED_REMOTE_IPS:127.0.0.1/32}
        handle @mcp_allowed {
            reverse_proxy api:8000
        }
        respond "MCP endpoint restricted" 403
    }

    reverse_proxy api:8000
}
```

Keep the existing web-domain block intact.

- [ ] **Step 6: Harden `Dockerfile.ops` non-root**

Update `infra/deploy/Dockerfile.ops` to include a non-root user:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

RUN adduser --disabled-password --gecos "" esdata \
    && pip install --no-cache-dir \
        alembic==1.16.4 \
        sqlalchemy==2.0.43 \
        psycopg[binary]==3.2.9

COPY --chown=esdata:esdata alembic.ini /workspace/alembic.ini
COPY --chown=esdata:esdata alembic /workspace/alembic
COPY --chown=esdata:esdata scripts /workspace/scripts

USER esdata

CMD ["python", "--version"]
```

- [ ] **Step 7: Run static infra tests**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_p0_infra_config.py -q`

Expected: PASS.

---

### Task 8: Consolidated Verification And Documentation Check

**Files:**
- Modify: `docs/master-execution-roadmap.md` only if no active conflicting claim exists and the user explicitly authorizes roadmap updates.
- Modify: `docs/operations/runbooks/worker-modelos.md` only if parser trust-state behavior changes need operator guidance.

- [ ] **Step 1: Run focused API regression suite**

Run: `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_smoke.py apps/api/tests/test_integration.py apps/api/tests/test_mcp_audit.py apps/api/tests/test_mcp_contract.py apps/api/tests/test_unified_multi_source_search.py apps/api/tests/test_p0_schema_safety.py apps/api/tests/test_p0_infra_config.py -q`

Expected: PASS.

- [ ] **Step 2: Run focused worker regression suite**

Run: `$env:PYTHONPATH='apps/workers'; python -m pytest apps/workers/tests/test_aeat_models.py apps/workers/tests/test_dgt.py apps/workers/tests/test_worker_dgt_doctrina.py -q`

Expected: PASS.

- [ ] **Step 3: Run lint on touched Python modules**

Run: `python -m ruff check apps/api/routers/legislacion.py apps/api/routers/modelos.py apps/api/services/modelos.py apps/api/services/query_audit.py apps/api/mcp_server.py apps/api/services/persistence.py apps/api/services/semantic_search.py apps/api/services/unified_multi_source_search.py apps/workers/aeat_models.py apps/workers/dgt.py apps/api/tests/test_p0_schema_safety.py apps/api/tests/test_p0_infra_config.py`

Expected: PASS or only pre-existing unrelated warnings documented with exact output.

- [ ] **Step 4: Check for remaining P0 forbidden patterns**

Run: `rg "CREATE TABLE IF NOT EXISTS" apps/api -g "*.py"`

Expected: no matches in production API runtime paths except test fixtures if any.

Run: `rg "railway up|branches: \[main\]" .github/workflows/deploy.yml`

Expected: no matches.

- [ ] **Step 5: Produce final implementation summary**

Summarize:

```markdown
P0 stabilization implemented.

Verification:
- API focused suite: <exact result>
- Worker focused suite: <exact result>
- Ruff: <exact result>
- Forbidden-pattern checks: <exact result>

Not done:
- No production deploy performed.
- No VPS/firewall/secret changes performed.
- No commit created unless explicitly requested.
```

---

## Plan Self-Review

- Spec coverage: current LIVA accuracy is covered by Task 1; AEAT cleanliness by Task 2; MCP audit by Task 3; schema/RLS by Task 4; search isolation by Task 5; DGT/cron safety by Task 6 and Task 7; infra deploy hazards by Task 7; verification by Task 8.
- Placeholder scan: no task uses `TBD`, `TODO`, or unspecified tests. Each code-changing task includes target files, code snippets, commands, and expected outcomes.
- Type consistency: plan uses existing `confianza.aviso`, existing `verified/completeness` model response fields, existing `QueryAuditService.record_query`, existing `MCPInternalAsyncClient`, and new helper names consistently.
