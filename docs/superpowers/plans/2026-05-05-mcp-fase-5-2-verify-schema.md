# MCP Fase 5.2 Verify Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `scripts/maintenance/verify_schema.py` so deploy gating fails when critical runtime tables or columns for `query_audit_log`, `dgt_queue`, and `documento_interpretativo` row-quality fields are missing, or when `dgt_queue` lacks the runtime-critical uniqueness used by `ON CONFLICT`.

**Architecture:** Keep `verify_schema.py` as a small structural gate driven by one `REQUIRED_SCHEMA` mapping plus one small uniqueness check dedicated to `dgt_queue(worker_name, source_entity_id)`. Add a focused script test suite in `scripts/tests/` that loads the maintenance module directly, builds disposable SQLite schemas, and proves both success and failure cases for the newly required tables, columns, and queue uniqueness contract.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest, Ruff

**Repo Note:** Do not commit or push as part of this plan unless the user explicitly asks.

---

## File Map

- Modify: `scripts/maintenance/verify_schema.py`
  Expand `REQUIRED_SCHEMA`, add the focused `dgt_queue` uniqueness check, and improve the success message while keeping the current script shape and exit-code contract.
- Create: `scripts/tests/test_verify_schema.py`
  Add direct regression coverage for the expanded schema gate using disposable SQLite schemas.
- Modify: `docs/master-execution-roadmap.md`
  Close `5.2` with fresh verification evidence and point the live summary to `5.3` if the implementation is green.
- Modify: `docs/operations/agent-notes.md`
  Record the reusable invariant that deploy schema gates should track current runtime-critical tables/columns, not just the table that triggered the last incident.

### Task 1: Add failing regressions for the expanded schema contract

**Files:**
- Create: `scripts/tests/test_verify_schema.py`
- Reference: `scripts/maintenance/verify_schema.py`
- Reference: `_legacy/scripts/test_verify_schema.py`
- Reference: `docs/superpowers/specs/2026-05-05-mcp-fase-5-2-verify-schema-design.md`

- [ ] **Step 1: Write the failing test file for the expanded contract**

```python
from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


MODULE_PATH = Path(__file__).resolve().parents[1] / "maintenance" / "verify_schema.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_schema", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_runtime_schema(engine) -> None:
    ddl = [
        """
        CREATE TABLE modelo_campana_operativa (
            campana_id INTEGER PRIMARY KEY,
            categoria_obligado TEXT,
            frecuencia_presentacion TEXT,
            ventana_presentacion TEXT,
            canal_presentacion TEXT,
            obligados_resumen TEXT,
            plazo_resumen TEXT,
            presentacion_resumen TEXT,
            norma_base TEXT,
            nota TEXT,
            actualizado_at TEXT,
            origen_metadato TEXT,
            estado_metadato TEXT
        )
        """,
        """
        CREATE TABLE query_audit_log (
            id INTEGER PRIMARY KEY,
            entry_id TEXT,
            request_id TEXT,
            path TEXT,
            query_text TEXT,
            retrieved_chunks TEXT,
            response_summary TEXT,
            tool_name TEXT,
            sources TEXT,
            confidence TEXT,
            completeness TEXT,
            verified INTEGER,
            grounding_status TEXT,
            prompt_injection_detected INTEGER,
            grounding_summary TEXT,
            response_payload TEXT,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE dgt_queue (
            id INTEGER PRIMARY KEY,
            worker_name TEXT,
            source_entity_id TEXT,
            dgt_url TEXT,
            status TEXT,
            queued_at TEXT,
            processed_at TEXT
        )
        """,
        "CREATE UNIQUE INDEX uq_dgt_queue_worker_source ON dgt_queue(worker_name, source_entity_id)",
        """
        CREATE TABLE documento_interpretativo (
            id INTEGER PRIMARY KEY,
            row_completeness TEXT,
            row_provenance TEXT
        )
        """,
    ]
    with engine.begin() as conn:
        for statement in ddl:
            conn.execute(text(statement))


def test_normalize_db_url_adds_psycopg_driver_for_plain_postgresql_scheme():
    module = _load_module()

    url = "postgresql://user:pass@host:5432/dbname"

    assert module.normalize_db_url(url) == "postgresql+psycopg://user:pass@host:5432/dbname"


def test_find_schema_issues_returns_empty_for_expanded_runtime_contract():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)

    issues = module.find_schema_issues(inspect(engine))

    assert issues == []


def test_find_schema_issues_reports_missing_query_audit_response_payload():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE query_audit_log"))
        conn.execute(
            text(
                """
                CREATE TABLE query_audit_log (
                    id INTEGER PRIMARY KEY,
                    entry_id TEXT,
                    request_id TEXT,
                    path TEXT,
                    query_text TEXT,
                    retrieved_chunks TEXT,
                    response_summary TEXT,
                    tool_name TEXT,
                    sources TEXT,
                    confidence TEXT,
                    completeness TEXT,
                    verified INTEGER,
                    grounding_status TEXT,
                    prompt_injection_detected INTEGER,
                    grounding_summary TEXT,
                    created_at TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert "missing column: query_audit_log.response_payload" in issues


def test_find_schema_issues_reports_missing_query_audit_entry_id():
    ...


def test_find_schema_issues_reports_missing_query_audit_created_at():
    ...


def test_find_schema_issues_reports_missing_dgt_queue_status():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE dgt_queue"))
        conn.execute(
            text(
                """
                CREATE TABLE dgt_queue (
                    id INTEGER PRIMARY KEY,
                    worker_name TEXT,
                    source_entity_id TEXT,
                    dgt_url TEXT,
                    queued_at TEXT,
                    processed_at TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert "missing column: dgt_queue.status" in issues


def test_find_schema_issues_reports_missing_dgt_queue_uniqueness():
    ...


def test_find_schema_issues_reports_missing_documento_interpretativo_row_provenance():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_runtime_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE documento_interpretativo"))
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY,
                    row_completeness TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert "missing column: documento_interpretativo.row_provenance" in issues


def test_find_schema_issues_reports_missing_table():
    module = _load_module()
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE modelo_campana_operativa (
                    campana_id INTEGER PRIMARY KEY,
                    categoria_obligado TEXT,
                    frecuencia_presentacion TEXT,
                    ventana_presentacion TEXT,
                    canal_presentacion TEXT,
                    obligados_resumen TEXT,
                    plazo_resumen TEXT,
                    presentacion_resumen TEXT,
                    norma_base TEXT,
                    nota TEXT,
                    actualizado_at TEXT,
                    origen_metadato TEXT,
                    estado_metadato TEXT
                )
                """
            )
        )

    issues = module.find_schema_issues(inspect(engine))

    assert "missing table: query_audit_log" in issues
    assert "missing table: dgt_queue" in issues
    assert "missing table: documento_interpretativo" in issues
```

- [ ] **Step 2: Run the new verify-schema tests to verify red**

Run: `python -m pytest scripts/tests/test_verify_schema.py -q`

Expected: FAIL because `verify_schema.py` still only knows about `modelo_campana_operativa`, so the new missing-column and missing-table expectations for `query_audit_log`, `dgt_queue`, and `documento_interpretativo` will not be reported yet.

- [ ] **Step 3: Optional commit, only if the user explicitly asks**

```bash
git add scripts/tests/test_verify_schema.py
git commit -m "test: add verify_schema runtime contract regressions"
```

### Task 2: Expand the schema gate implementation and prove it green

**Files:**
- Modify: `scripts/maintenance/verify_schema.py`
- Modify: `scripts/tests/test_verify_schema.py`

- [ ] **Step 1: Expand `REQUIRED_SCHEMA` with the approved runtime tables**

```python
REQUIRED_SCHEMA = {
    "modelo_campana_operativa": {
        "campana_id",
        "categoria_obligado",
        "frecuencia_presentacion",
        "ventana_presentacion",
        "canal_presentacion",
        "obligados_resumen",
        "plazo_resumen",
        "presentacion_resumen",
        "norma_base",
        "nota",
        "actualizado_at",
        "origen_metadato",
        "estado_metadato",
    },
    "query_audit_log": {
        "entry_id",
        "request_id",
        "path",
        "query_text",
        "retrieved_chunks",
        "response_summary",
        "tool_name",
        "sources",
        "confidence",
        "completeness",
        "verified",
        "grounding_status",
        "prompt_injection_detected",
        "grounding_summary",
        "response_payload",
        "created_at",
    },
    "dgt_queue": {
        "worker_name",
        "source_entity_id",
        "dgt_url",
        "status",
        "queued_at",
        "processed_at",
    },
    "documento_interpretativo": {
        "row_completeness",
        "row_provenance",
    },
}
```

- [ ] **Step 1b: Add the focused `dgt_queue` uniqueness check**

```python
def find_dgt_queue_uniqueness_issues(db_inspector) -> list[str]:
    tables = set(db_inspector.get_table_names())
    if "dgt_queue" not in tables:
        return []

    expected = {"worker_name", "source_entity_id"}
    for index in db_inspector.get_indexes("dgt_queue"):
        if index.get("unique") and set(index.get("column_names") or []) == expected:
            return []

    unique_constraints = getattr(db_inspector, "get_unique_constraints", None)
    if callable(unique_constraints):
        for constraint in unique_constraints("dgt_queue"):
            if set(constraint.get("column_names") or []) == expected:
                return []

    return [
        "missing unique key: dgt_queue(worker_name, source_entity_id)"
    ]
```

- [ ] **Step 2: Keep the current issue reporting contract and make the success message explicit**

```python
issues = find_schema_issues(inspect(engine))
issues.extend(find_dgt_queue_uniqueness_issues(inspect(engine)))

if issues:
    print("SCHEMA VERIFICATION FAILED", file=sys.stderr)
    for issue in issues:
        print(f"- {issue}", file=sys.stderr)
    return 1

print(
    "Schema OK: modelo_campana_operativa, query_audit_log, dgt_queue, "
    "documento_interpretativo runtime columns present and dgt_queue uniqueness enforced"
)
return 0
```

- [ ] **Step 3: Run the verify-schema tests to verify green**

Run: `python -m pytest scripts/tests/test_verify_schema.py -q`

Expected: PASS, proving the gate now fails on missing runtime-critical tables/columns and stays green when the expanded contract exists.

- [ ] **Step 4: Run focused lint for the maintenance script and its tests**

Run: `python -m ruff check scripts/maintenance/verify_schema.py scripts/tests/test_verify_schema.py --select F,I`

Expected: `All checks passed!`

- [ ] **Step 5: Record the exact non-destructive verification used for this phase**

Run: `python -m pytest scripts/tests/test_verify_schema.py -q`

Expected: reuse the green suite as the fresh non-destructive verification for the script logic in this phase.

- [ ] **Step 6: Optional commit, only if the user explicitly asks**

```bash
git add scripts/maintenance/verify_schema.py scripts/tests/test_verify_schema.py
git commit -m "fix: expand deploy schema verification gate"
```

### Task 3: Close docs for Fase 5.2 with fresh evidence

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`
- Reference: `docs/superpowers/specs/2026-05-05-mcp-fase-5-2-verify-schema-design.md`

- [ ] **Step 1: Update the roadmap live summary to close `5.2` and point to `5.3`**

```md
- Objetivo actual: preparar **Fase 5.3** del plan MCP para alinear env vars reales con runtime.
- Estado actual: **Fase 5.2** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; **Fase 5.3** queda pendiente de confirmacion explicita del usuario antes de abrirse.
- Estado del agente activo: `5.2` cerrada con evidencia fresca; `verify_schema.py` ya valida las tablas/columnas minimas de `modelo_campana_operativa`, `query_audit_log`, `dgt_queue` y `documento_interpretativo` requeridas por el runtime actual.
- Reclamo actual: `[SIN RECLAMO]` sin archivos reclamados tras el cierre de `5.2`.
- Siguiente paso exacto: pedir confirmacion del usuario para abrir **Fase 5.3** (`infra/deploy/docker-compose.prod.yml`, `infra/deploy/compose.env.example`, `docs/environment-variables.md`).
```

- [ ] **Step 2: Add the `5.2` historical note with exact evidence**

```md
- Nota 2026-05-05: Fase 5.2 `[COMPLETA]` cerrada en `G:\_Proyectos\esdata\.worktrees\next-task`. Resultado: `scripts/maintenance/verify_schema.py` deja de validar solo `modelo_campana_operativa` y pasa a cubrir tambien `query_audit_log`, `dgt_queue` y `documento_interpretativo` row-quality columns como gate estructural minimo del runtime actual. Evidencia fresca del cierre: `python -m pytest scripts/tests/test_verify_schema.py -q` -> `<N> passed`; `python -m ruff check scripts/maintenance/verify_schema.py scripts/tests/test_verify_schema.py --select F,I` -> `All checks passed!`. Riesgo residual explicitado: el gate sigue sin comprobar indices, constraints, seeds ni datos reales; ese hardening queda fuera de `5.2`.
```

- [ ] **Step 3: Add the reusable deploy/schema-gate note to `docs/operations/agent-notes.md`**

```md
### 2026-05-05 - verify_schema debe seguir el runtime actual, no solo la ultima tabla incidentada

- Scope: `scripts/maintenance/verify_schema.py`, deploy Compose con contenedor `ops`
- Hallazgo: dejar `verify_schema.py` anclado a una sola tabla historica da falsos verdes cuando el runtime ya depende de otras migraciones recientes.
- Impacto: un deploy puede pasar `alembic upgrade head` y aun asi quedar roto para MCP, DGT o row-quality si el gate no exige esas columnas nuevas.
- Regla practica: cuando una fase MCP introduce una dependencia estructural nueva y el deploy la necesita para arrancar sano, evaluar si `verify_schema.py` debe ampliarse en el mismo bloque de hardening operativo o en el siguiente slice de deploy gating.
```

- [ ] **Step 4: Re-run the focused verification after docs updates**

Run: `python -m pytest scripts/tests/test_verify_schema.py -q`

Expected: PASS, confirming the closure note reflects fresh evidence.

- [ ] **Step 5: Optional commit, only if the user explicitly asks**

```bash
git add docs/master-execution-roadmap.md docs/operations/agent-notes.md docs/superpowers/plans/2026-05-05-mcp-fase-5-2-verify-schema.md
git commit -m "docs: record verify_schema deploy gate expansion"
```
