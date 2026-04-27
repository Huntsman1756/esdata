# legalize-es Fase 12 Minimal Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first `Fase 12` slice for `legalize-es` using a local `CC` markdown fixture, parsing articles into the existing legislation pipeline so the content is searchable and retrievable through the current API.

**Architecture:** Keep the current `norma -> articulo -> version_articulo -> API` pipeline unchanged. Add one small worker that parses a controlled markdown fixture, upserts normalized legislation rows into the existing schema, and prove the result end-to-end with worker tests plus API search/detail tests. No external clone, no new endpoints, no schema redesign.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, SQLite test fixtures, existing legislation search service.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `apps/workers/legalize_es.py` | Create | Parse local markdown fixtures and upsert `CC` articles into legislation tables |
| `apps/workers/tests/test_legalize_es.py` | Create | Parser/upsert/idempotency tests for `legalize-es` worker |
| `apps/workers/tests/fixtures/legalize_es/cc.md` | Create | Controlled markdown fixture for first `CC` ingestion slice |
| `apps/api/tests/test_search_legislacion.py` | Modify | Verify search sees `CC` content after ingestion |
| `apps/api/tests/test_integration.py` | Modify or keep untouched | Only extend if needed for API-level detail validation |
| `docs/master-execution-roadmap.md` | Modify later | Update phase status after implementation, not during this plan-writing pass |

---

## Task 1: Add the controlled `CC` markdown fixture and parser tests

**Files:**
- Create: `apps/workers/tests/fixtures/legalize_es/cc.md`
- Create: `apps/workers/tests/test_legalize_es.py`

- [ ] **Step 1: Create the markdown fixture**

Create `apps/workers/tests/fixtures/legalize_es/cc.md` with this exact content:

```md
# Codigo Civil

Fuente: legalize-es
Codigo: CC
Fecha version: 2025-01-01

Articulo 1.

Las fuentes del ordenamiento juridico espanol son la ley, la costumbre y los principios generales del derecho.

Articulo 2.

Las leyes entraran en vigor a los veinte dias de su completa publicacion en el boletin oficial del Estado, si en ellas no se dispone otra cosa.
```

- [ ] **Step 2: Write the failing parser tests**

Create `apps/workers/tests/test_legalize_es.py` with this initial content:

```python
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legalize_es import parse_markdown_norma, run_sync


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "legalize_es" / "cc.md"


def _create_schema(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE norma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                boe_id TEXT,
                eli_uri TEXT,
                jurisdiccion TEXT NOT NULL,
                tipo_fuente TEXT NOT NULL,
                tipo_documento TEXT NOT NULL,
                ambito TEXT NOT NULL,
                estado_cobertura TEXT NOT NULL,
                vigente_desde TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                norma_id INTEGER NOT NULL,
                numero TEXT NOT NULL,
                titulo TEXT,
                tipo TEXT NOT NULL,
                UNIQUE (norma_id, numero)
            )
        """))
        conn.execute(text("""
            CREATE TABLE version_articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                articulo_id INTEGER NOT NULL,
                texto TEXT NOT NULL,
                vigente_desde TEXT NOT NULL,
                vigente_hasta TEXT,
                boe_bloque_id TEXT
            )
        """))


def test_parse_markdown_norma_extracts_cc_articles():
    parsed = parse_markdown_norma(FIXTURE_PATH)

    assert parsed["codigo"] == "CC"
    assert parsed["titulo"] == "Codigo Civil"
    assert parsed["vigente_desde"] == "2025-01-01"
    assert len(parsed["articulos"]) == 2
    assert parsed["articulos"][0]["numero"] == "1"
    assert "fuentes del ordenamiento juridico" in parsed["articulos"][0]["texto"].lower()


def test_run_sync_upserts_norma_articulo_and_version_once():
    engine = create_engine("sqlite:///:memory:", future=True)
    _create_schema(engine)

    result_first = run_sync(engine, fixture_paths=[FIXTURE_PATH])
    result_second = run_sync(engine, fixture_paths=[FIXTURE_PATH])

    with engine.begin() as conn:
        norma_count = conn.execute(text("SELECT COUNT(*) FROM norma WHERE codigo = 'CC'" )).scalar_one()
        articulo_count = conn.execute(text("SELECT COUNT(*) FROM articulo" )).scalar_one()
        version_count = conn.execute(text("SELECT COUNT(*) FROM version_articulo" )).scalar_one()

    assert result_first["normas_upserted"] == 1
    assert result_first["articulos_upserted"] == 2
    assert result_first["versiones_upserted"] == 2
    assert result_second["normas_upserted"] == 0
    assert result_second["articulos_upserted"] == 0
    assert result_second["versiones_upserted"] == 0
    assert norma_count == 1
    assert articulo_count == 2
    assert version_count == 2
```

- [ ] **Step 3: Run parser tests to verify they fail**

Run:

```bash
pytest apps/workers/tests/test_legalize_es.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'legalize_es'`.

- [ ] **Step 4: Commit**

```bash
git add apps/workers/tests/fixtures/legalize_es/cc.md apps/workers/tests/test_legalize_es.py
git commit -m "test(worker): add legalize-es cc fixture and failing parser tests"
```

---

## Task 2: Implement the minimal `legalize-es` worker

**Files:**
- Create: `apps/workers/legalize_es.py`

- [ ] **Step 1: Create `apps/workers/legalize_es.py`**

Create this file:

```python
#!/usr/bin/env python

import argparse
import os
import re
from pathlib import Path

from sqlalchemy import create_engine, text

from runtime import configure_logging, get_database_url

DATABASE_URL = get_database_url()
logger = configure_logging("worker-legalize-es")


ARTICLE_RE = re.compile(r"^Articulo\s+(\d+)\.\s*$", re.IGNORECASE)


def parse_markdown_norma(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in content.splitlines()]

    title = lines[0].lstrip("# ").strip()
    codigo = next(line.split(":", 1)[1].strip() for line in lines if line.startswith("Codigo:"))
    vigente_desde = next(line.split(":", 1)[1].strip() for line in lines if line.startswith("Fecha version:"))

    articulos: list[dict] = []
    current_numero = None
    current_text: list[str] = []

    for line in lines:
        match = ARTICLE_RE.match(line.strip())
        if match:
            if current_numero is not None:
                articulos.append(
                    {
                        "numero": current_numero,
                        "texto": " ".join(part for part in current_text if part).strip(),
                        "vigente_desde": vigente_desde,
                    }
                )
            current_numero = match.group(1)
            current_text = []
            continue

        if current_numero is not None:
            current_text.append(line.strip())

    if current_numero is not None:
        articulos.append(
            {
                "numero": current_numero,
                "texto": " ".join(part for part in current_text if part).strip(),
                "vigente_desde": vigente_desde,
            }
        )

    return {
        "codigo": codigo,
        "titulo": title,
        "tipo_fuente": "legalize_es",
        "tipo_documento": "ley",
        "ambito": "civil",
        "estado_cobertura": "ingestada",
        "vigente_desde": vigente_desde,
        "source_path": str(path),
        "articulos": articulos,
    }


def _upsert_norma(conn, parsed: dict) -> tuple[int, int]:
    row = conn.execute(
        text("SELECT id FROM norma WHERE codigo = :codigo"),
        {"codigo": parsed["codigo"]},
    ).first()
    if row:
        return row[0], 0

    result = conn.execute(
        text(
            """
            INSERT INTO norma (
                codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
                tipo_documento, ambito, estado_cobertura, vigente_desde
            )
            VALUES (
                :codigo, :titulo, NULL, :eli_uri, 'es', :tipo_fuente,
                :tipo_documento, :ambito, :estado_cobertura, :vigente_desde
            )
            """
        ),
        {
            "codigo": parsed["codigo"],
            "titulo": parsed["titulo"],
            "eli_uri": parsed["source_path"],
            "tipo_fuente": parsed["tipo_fuente"],
            "tipo_documento": parsed["tipo_documento"],
            "ambito": parsed["ambito"],
            "estado_cobertura": parsed["estado_cobertura"],
            "vigente_desde": parsed["vigente_desde"],
        },
    )
    norma_id = result.lastrowid
    return norma_id, 1


def _upsert_articulo(conn, norma_id: int, numero: str) -> tuple[int, int]:
    row = conn.execute(
        text("SELECT id FROM articulo WHERE norma_id = :norma_id AND numero = :numero"),
        {"norma_id": norma_id, "numero": numero},
    ).first()
    if row:
        return row[0], 0

    result = conn.execute(
        text(
            """
            INSERT INTO articulo (norma_id, numero, titulo, tipo)
            VALUES (:norma_id, :numero, NULL, 'articulo')
            """
        ),
        {"norma_id": norma_id, "numero": numero},
    )
    return result.lastrowid, 1


def _upsert_version_articulo(conn, articulo_id: int, texto_articulo: str, vigente_desde: str) -> int:
    row = conn.execute(
        text(
            """
            SELECT id FROM version_articulo
            WHERE articulo_id = :articulo_id AND vigente_desde = :vigente_desde
            """
        ),
        {"articulo_id": articulo_id, "vigente_desde": vigente_desde},
    ).first()
    if row:
        return 0

    conn.execute(
        text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            VALUES (:articulo_id, :texto, :vigente_desde, NULL, NULL)
            """
        ),
        {"articulo_id": articulo_id, "texto": texto_articulo, "vigente_desde": vigente_desde},
    )
    return 1


def run_sync(engine, fixture_paths: list[Path]):
    normas_upserted = 0
    articulos_upserted = 0
    versiones_upserted = 0

    with engine.begin() as conn:
        for path in fixture_paths:
            parsed = parse_markdown_norma(Path(path))
            norma_id, norma_inserted = _upsert_norma(conn, parsed)
            normas_upserted += norma_inserted

            for articulo in parsed["articulos"]:
                articulo_id, articulo_inserted = _upsert_articulo(conn, norma_id, articulo["numero"])
                articulos_upserted += articulo_inserted
                versiones_upserted += _upsert_version_articulo(
                    conn,
                    articulo_id,
                    articulo["texto"],
                    articulo["vigente_desde"],
                )

    logger.info(
        "legalize-es sync complete: %s normas, %s articulos, %s versiones",
        normas_upserted,
        articulos_upserted,
        versiones_upserted,
    )
    return {
        "normas_upserted": normas_upserted,
        "articulos_upserted": articulos_upserted,
        "versiones_upserted": versiones_upserted,
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest local legalize-es markdown fixtures")
    parser.add_argument("--db-url", help="Database URL")
    parser.add_argument("--fixture", action="append", default=[], help="Path to markdown fixture")
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL", DATABASE_URL)
    fixture_paths = [Path(item) for item in args.fixture]
    engine = create_engine(db_url)
    run_sync(engine, fixture_paths=fixture_paths)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the worker tests and verify they pass**

Run:

```bash
pytest apps/workers/tests/test_legalize_es.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/workers/legalize_es.py apps/workers/tests/test_legalize_es.py apps/workers/tests/fixtures/legalize_es/cc.md
git commit -m "feat(worker): add minimal legalize-es cc ingestion worker"
```

---

## Task 3: Prove that legislation search sees the ingested `CC` content

**Files:**
- Modify: `apps/api/tests/test_search_legislacion.py`

- [ ] **Step 1: Add the failing search test**

Append this test to `apps/api/tests/test_search_legislacion.py`:

```python
def test_search_legislacion_returns_cc_after_legalize_seed(db_url):
    import os
    from sqlalchemy import create_engine, text
    from apps.workers.legalize_es import run_sync

    os.environ["DATABASE_URL"] = db_url
    engine = create_engine(db_url, future=True)

    fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "cc.md"

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CC'))"))
        conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CC')"))
        conn.execute(text("DELETE FROM norma WHERE codigo = 'CC'"))

    run_sync(engine, fixture_paths=[fixture])
    result = search_legislacion("ordenamiento", norma="CC")

    assert result["resultados"]
    assert any(row["norma"] == "CC" for row in result["resultados"])
```

- [ ] **Step 2: Run the search test to verify current behavior**

Run:

```bash
pytest apps/api/tests/test_search_legislacion.py::test_search_legislacion_returns_cc_after_legalize_seed -v
```

Expected: it may FAIL initially if the search service or fixture assumptions need adjustment.

- [ ] **Step 3: Adjust the test data only if required by existing search behavior**

If the test fails because `search_legislacion()` requires specific searchable fields or ranking assumptions already present in this repo, keep the production code unchanged and only adapt the test setup so that the inserted `CC` rows satisfy the existing search contract.

Allowed adjustments:

```python
# If needed, reuse existing seeded_db conventions and only assert:
assert isinstance(result["resultados"], list)
assert any(row.get("norma") == "CC" for row in result["resultados"])
```

Do not redesign the search service in this slice.

- [ ] **Step 4: Re-run the search test until it passes**

Run:

```bash
pytest apps/api/tests/test_search_legislacion.py::test_search_legislacion_returns_cc_after_legalize_seed -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_search_legislacion.py
git commit -m "test(api): verify legalize-es cc content is searchable"
```

---

## Task 4: Prove article detail works with `vigente_en`

**Files:**
- Modify: `apps/api/tests/test_integration.py`

- [ ] **Step 1: Add the failing API detail test**

Append this test to `apps/api/tests/test_integration.py`:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_cc_articulo_detail_with_vigente_en_after_legalize_seed(seeded_db):
    from pathlib import Path
    from apps.workers.legalize_es import run_sync

    fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "cc.md"
    run_sync(engine, fixture_paths=[fixture])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/v1/legislacion/CC/articulos/1?vigente_en=2025-01-02")

    assert r.status_code == 200
    data = r.json()
    assert data["norma"] == "CC"
    assert data["numero"] == "1"
    assert "ordenamiento juridico" in data["texto"].lower()
```

- [ ] **Step 2: Run the integration detail test to verify behavior**

Run:

```bash
pytest apps/api/tests/test_integration.py::test_cc_articulo_detail_with_vigente_en_after_legalize_seed -v
```

Expected: it may FAIL first if the fixture path or import path needs adjustment.

- [ ] **Step 3: Fix only the test harness if needed**

Allowed fixes:

```python
# Use the same engine/test harness objects already present in test_integration.py.
# Keep the production legislation router unchanged unless a real bug appears.
```

Do not add a new endpoint or change the router contract in this slice.

- [ ] **Step 4: Re-run the integration detail test until it passes**

Run:

```bash
pytest apps/api/tests/test_integration.py::test_cc_articulo_detail_with_vigente_en_after_legalize_seed -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_integration.py
git commit -m "test(api): verify legalize-es cc article detail with vigente_en"
```

---

## Task 5: Verify the full `Fase 12` minimal slice

**Files:**
- No new files; verification only

- [ ] **Step 1: Run all focused tests for the slice**

Run:

```bash
pytest apps/workers/tests/test_legalize_es.py apps/api/tests/test_search_legislacion.py apps/api/tests/test_integration.py -k "legalize or cc_articulo or search_legislacion_returns_cc" -v
```

Expected: PASS.

- [ ] **Step 2: Run a syntax/import check for the new worker**

Run:

```bash
python -m py_compile apps/workers/legalize_es.py
```

Expected: no output, exit code 0.

- [ ] **Step 3: Optional manual smoke run of the worker**

Run:

```bash
python apps/workers/legalize_es.py --db-url "sqlite:///:memory:" --fixture "apps/workers/tests/fixtures/legalize_es/cc.md"
```

Expected: worker logs completion without crashing.

- [ ] **Step 4: Commit verification checkpoint**

```bash
git status
```

Expected: clean worktree or only intentional pending docs updates.

---

## Coverage Check

- The slice uses markdown as raw source only.
- The parser is intentionally minimal and article-only.
- The existing legislation schema is reused without redesign.
- Search and detail are validated through current API surfaces.
- No frontend logic or markdown-as-database behavior is introduced.

## Placeholder Scan

- No `TODO`, `TBD`, or implicit future work inside tasks.
- Each task names exact files and commands.
- Code steps contain complete snippets.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-25-legalize-es-fase-12.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
