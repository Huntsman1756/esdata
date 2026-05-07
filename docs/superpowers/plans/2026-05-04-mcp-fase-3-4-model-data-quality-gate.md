# MCP Fase 3.4 Model Data Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic model-data quality gate that detects non-canonical AEAT/BOE hosts, weak `modelo_articulo` provenance, suspicious pseudo-norma values, and curated-metadata state drift in both source files and seeded DB data.

**Architecture:** Implement one maintenance script with two check families: static inspection of the approved AEAT seed/script files and DB-backed checks over the persisted `modelos` tables. Keep the script intentionally narrow, return structured findings, add dedicated tests in `scripts/tests/`, and wire the script into the existing DB-backed CI job after migrations.

**Tech Stack:** Python 3.12, `sqlalchemy`, `pytest`, GitHub Actions CI

---

### Task 1: Add failing tests for static and DB findings

**Files:**
- Create: `scripts/tests/test_check_model_data_quality.py`
- Reference: `scripts/tests/test_verify_doc_artifacts.py`
- Reference: `docs/superpowers/specs/2026-05-04-mcp-fase-3-4-model-data-quality-gate-design.md`

- [ ] **Step 1: Write the failing test file with static and DB quality cases**

```python
from __future__ import annotations

import importlib.util
import shutil
import sqlite3
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "maintenance" / "check_model_data_quality.py"
SPEC = importlib.util.spec_from_file_location("check_model_data_quality", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".tmp_check_model_data_quality"


def _reset_tmp_dir() -> Path:
    if TEST_TMP_ROOT.exists():
        shutil.rmtree(TEST_TMP_ROOT)
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return TEST_TMP_ROOT


def _sqlite_db_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _create_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE aeat_modelo (
                id INTEGER PRIMARY KEY,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                periodo TEXT,
                impuesto TEXT,
                url_info TEXT
            );

            CREATE TABLE modelo_campana (
                id INTEGER PRIMARY KEY,
                modelo_id INTEGER NOT NULL,
                campana TEXT NOT NULL,
                url_instrucciones TEXT,
                url_normativa TEXT,
                url_formato TEXT
            );

            CREATE TABLE modelo_normativa (
                id INTEGER PRIMARY KEY,
                modelo_id INTEGER NOT NULL,
                boe_id TEXT,
                titulo TEXT NOT NULL,
                url_boe TEXT
            );

            CREATE TABLE modelo_articulo (
                modelo_id INTEGER NOT NULL,
                articulo_id INTEGER,
                casilla TEXT,
                nota TEXT,
                fuente TEXT NOT NULL,
                url_fuente TEXT,
                norma TEXT,
                numero TEXT,
                metodo_enlace TEXT,
                confianza_enlace REAL
            );

            CREATE TABLE modelo_campana_operativa (
                campana_id INTEGER PRIMARY KEY,
                origen_metadato TEXT,
                estado_metadato TEXT,
                nota TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_find_static_url_issues_flags_non_canonical_host():
    tmp_dir = _reset_tmp_dir()
    seed_file = tmp_dir / "seed-modelos.py"
    seed_file.write_text(
        'URLS = ["https://agenciatributaria.gob.es/modelo-100"]\n',
        encoding="utf-8",
    )

    findings = MODULE.find_static_url_issues(seed_file)

    assert len(findings) == 1
    assert findings[0]["check_id"] == "static.non_canonical_host"


def test_find_static_url_issues_accepts_canonical_hosts():
    tmp_dir = _reset_tmp_dir()
    seed_file = tmp_dir / "seed-modelos.py"
    seed_file.write_text(
        'URLS = ["https://sede.agenciatributaria.gob.es/modelo-100", "https://www.boe.es/x"]\n',
        encoding="utf-8",
    )

    findings = MODULE.find_static_url_issues(seed_file)

    assert findings == []


def test_find_modelo_articulo_issues_flags_weak_provenance():
    tmp_dir = _reset_tmp_dir()
    db_path = tmp_dir / "quality.sqlite3"
    _create_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO modelo_articulo (modelo_id, articulo_id, fuente, url_fuente, norma, numero, metodo_enlace, confianza_enlace) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "seed", "https://sede.agenciatributaria.gob.es/modelo-100", "LIRPF", "96", "legacy_numero_only", 0.0),
        )
        conn.commit()
    finally:
        conn.close()

    findings = MODULE.find_db_issues(_sqlite_db_url(db_path))

    assert any(f["check_id"] == "db.modelo_articulo_weak_provenance" for f in findings)


def test_find_modelo_articulo_issues_flags_suspicious_norma_value():
    tmp_dir = _reset_tmp_dir()
    db_path = tmp_dir / "quality.sqlite3"
    _create_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO modelo_articulo (modelo_id, articulo_id, fuente, url_fuente, norma, numero, metodo_enlace, confianza_enlace) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "seed", "https://sede.agenciatributaria.gob.es/modelo-303", "IVA", "91", "manual_official", 1.0),
        )
        conn.commit()
    finally:
        conn.close()

    findings = MODULE.find_db_issues(_sqlite_db_url(db_path))

    assert any(f["check_id"] == "db.modelo_articulo_suspicious_norma" for f in findings)


def test_find_operativa_issues_flags_curated_draft_conflict():
    tmp_dir = _reset_tmp_dir()
    db_path = tmp_dir / "quality.sqlite3"
    _create_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO modelo_campana_operativa (campana_id, origen_metadato, estado_metadato, nota) VALUES (?, ?, ?, ?)",
            (1, "seed_curado", "borrador", "metadato operativo curado"),
        )
        conn.commit()
    finally:
        conn.close()

    findings = MODULE.find_db_issues(_sqlite_db_url(db_path))

    assert any(f["check_id"] == "db.operativa_curated_state_conflict" for f in findings)


def test_run_returns_one_when_findings_exist():
    tmp_dir = _reset_tmp_dir()
    seed_file = tmp_dir / "seed-modelos.py"
    seed_file.write_text('URL = "https://agenciatributaria.gob.es/modelo-100"\n', encoding="utf-8")

    exit_code, findings = MODULE.run(
        static_paths=[seed_file],
        db_url=None,
        static_only=True,
    )

    assert exit_code == 1
    assert len(findings) == 1


def test_run_returns_zero_when_no_findings_exist():
    tmp_dir = _reset_tmp_dir()
    seed_file = tmp_dir / "seed-modelos.py"
    seed_file.write_text(
        'URL = "https://sede.agenciatributaria.gob.es/modelo-100"\n',
        encoding="utf-8",
    )

    exit_code, findings = MODULE.run(
        static_paths=[seed_file],
        db_url=None,
        static_only=True,
    )

    assert exit_code == 0
    assert findings == []
```

- [ ] **Step 2: Run the new test file to verify it fails**

Run: `python -m pytest scripts/tests/test_check_model_data_quality.py -q`
Expected: FAIL with `FileNotFoundError` or import/setup failures because `scripts/maintenance/check_model_data_quality.py` does not exist yet.

- [ ] **Step 3: Commit the failing test scaffold only after confirming red**

```bash
git add scripts/tests/test_check_model_data_quality.py
git commit -m "test(scripts): add failing model data quality gate tests"
```

### Task 2: Implement the maintenance script with minimal static and DB checks

**Files:**
- Create: `scripts/maintenance/check_model_data_quality.py`
- Test: `scripts/tests/test_check_model_data_quality.py`
- Reference: `scripts/maintenance/verify_schema.py`

- [ ] **Step 1: Create the initial script structure and finding model**

```python
#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATIC_PATHS = [
    ROOT / "scripts" / "seed-modelos.py",
    ROOT / "scripts" / "seed-modelos-v2.py",
    ROOT / "scripts" / "data" / "seed_modelo_articulo.py",
]
CANONICAL_AEAT_HOST = "sede.agenciatributaria.gob.es"
CANONICAL_BOE_HOST = "www.boe.es"
SUSPICIOUS_NORMA_VALUES = {
    "IRPF",
    "IS",
    "IVA",
    "OP.347",
    "FACTA",
    "IVA.A",
    "IRPF.T",
    "DAC2",
    "SII",
    "BIEN.EX",
    "PROV.NR",
}
URL_RE = re.compile(r"https?://[^\s'\"`]+")


@dataclass
class Finding:
    check_id: str
    severity: str
    location: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 2: Implement URL helpers and static checks**

```python
def normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + db_url.removeprefix("postgresql://")
    return db_url


def classify_url_host(raw_url: str) -> str | None:
    parsed = urlparse(raw_url)
    return parsed.hostname.lower() if parsed.hostname else None


def _allowed_host_for_url(raw_url: str) -> str | None:
    host = classify_url_host(raw_url)
    if host == CANONICAL_AEAT_HOST:
        return CANONICAL_AEAT_HOST
    if host == CANONICAL_BOE_HOST:
        return CANONICAL_BOE_HOST
    return None


def find_static_url_issues(path: Path) -> list[dict]:
    findings: list[Finding] = []
    content = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(content.splitlines(), start=1):
        for raw_url in URL_RE.findall(line):
            if raw_url.startswith("http://"):
                findings.append(
                    Finding(
                        check_id="static.http_url",
                        severity="high",
                        location=f"{path}:{line_no}",
                        message=f"Non-HTTPS model source URL: {raw_url}",
                    )
                )
                continue
            if _allowed_host_for_url(raw_url) is None:
                findings.append(
                    Finding(
                        check_id="static.non_canonical_host",
                        severity="high",
                        location=f"{path}:{line_no}",
                        message=f"Non-canonical model source host: {raw_url}",
                    )
                )
    return [finding.to_dict() for finding in findings]
```

- [ ] **Step 3: Implement DB checks for `modelo_articulo` and `modelo_campana_operativa`**

```python
def find_db_issues(db_url: str) -> list[dict]:
    engine = create_engine(normalize_db_url(db_url), future=True)
    findings: list[Finding] = []
    try:
        with engine.connect() as conn:
            weak_rows = conn.execute(
                text(
                    """
                    SELECT modelo_id, norma, numero, metodo_enlace, confianza_enlace, url_fuente
                    FROM modelo_articulo
                    WHERE COALESCE(TRIM(url_fuente), '') = ''
                       OR metodo_enlace != 'manual_official'
                       OR confianza_enlace != 1.0
                    """
                )
            ).mappings()
            for row in weak_rows:
                findings.append(
                    Finding(
                        check_id="db.modelo_articulo_weak_provenance",
                        severity="high",
                        location=f"modelo_articulo:modelo_id={row['modelo_id']},norma={row.get('norma')},numero={row.get('numero')}",
                        message="modelo_articulo row does not meet strong provenance contract",
                    )
                )

            suspicious_rows = conn.execute(
                text(
                    """
                    SELECT modelo_id, norma, numero
                    FROM modelo_articulo
                    WHERE norma IN :suspicious_values
                    """
                ),
                {"suspicious_values": tuple(SUSPICIOUS_NORMA_VALUES)},
            ).mappings()
            for row in suspicious_rows:
                findings.append(
                    Finding(
                        check_id="db.modelo_articulo_suspicious_norma",
                        severity="medium",
                        location=f"modelo_articulo:modelo_id={row['modelo_id']},norma={row['norma']},numero={row.get('numero')}",
                        message=f"Suspicious pseudo-norma value in modelo_articulo.norma: {row['norma']}",
                    )
                )

            operativa_rows = conn.execute(
                text(
                    """
                    SELECT campana_id, origen_metadato, estado_metadato
                    FROM modelo_campana_operativa
                    WHERE (origen_metadato IN ('seed_curado', 'manual_curado') AND estado_metadato IN ('borrador', 'inferido'))
                       OR (origen_metadato = 'worker_derivado' AND estado_metadato = 'curado')
                    """
                )
            ).mappings()
            for row in operativa_rows:
                findings.append(
                    Finding(
                        check_id="db.operativa_curated_state_conflict",
                        severity="high",
                        location=f"modelo_campana_operativa:campana_id={row['campana_id']}",
                        message=(
                            "modelo_campana_operativa has inconsistent curated provenance/state "
                            f"({row['origen_metadato']} / {row['estado_metadato']})"
                        ),
                    )
                )
    finally:
        engine.dispose()
    return [finding.to_dict() for finding in findings]
```

- [ ] **Step 4: Add DB host checks and the `run()` / CLI entrypoint**

```python
def _append_url_host_findings(findings: list[Finding], table: str, key: str, column: str, raw_url: str | None) -> None:
    if raw_url is None or not str(raw_url).strip():
        return
    if str(raw_url).startswith("http://"):
        findings.append(
            Finding(
                check_id=f"db.{table}_http_url",
                severity="high",
                location=f"{table}:{key}",
                message=f"Non-HTTPS URL in {table}.{column}: {raw_url}",
            )
        )
        return
    if _allowed_host_for_url(str(raw_url)) is None:
        findings.append(
            Finding(
                check_id=f"db.{table}_non_canonical_host",
                severity="high",
                location=f"{table}:{key}",
                message=f"Non-canonical host in {table}.{column}: {raw_url}",
            )
        )


def run(static_paths: list[Path] | None = None, db_url: str | None = None, static_only: bool = False, db_only: bool = False) -> tuple[int, list[dict]]:
    if static_only and db_only:
        return 2, []

    findings: list[dict] = []
    selected_paths = static_paths or DEFAULT_STATIC_PATHS

    if not db_only:
        for path in selected_paths:
            findings.extend(find_static_url_issues(path))

    resolved_db_url = db_url or os.getenv("DATABASE_URL")
    if not static_only:
        if not resolved_db_url:
            return 2, findings
        findings.extend(find_db_issues(resolved_db_url))

    return (1 if findings else 0), findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check model data quality guardrails")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON")
    parser.add_argument("--db-url", help="Override DATABASE_URL")
    parser.add_argument("--static-only", action="store_true", help="Run only static checks")
    parser.add_argument("--db-only", action="store_true", help="Run only DB checks")
    args = parser.parse_args()

    exit_code, findings = run(
        db_url=args.db_url,
        static_only=args.static_only,
        db_only=args.db_only,
    )
    if args.json:
        print(json.dumps({"total": len(findings), "findings": findings}, indent=2, ensure_ascii=False))
    else:
        if findings:
            print("MODEL DATA QUALITY CHECK FAILED", file=sys.stderr)
            for finding in findings:
                print(f"- [{finding['severity']}] {finding['check_id']} {finding['location']}: {finding['message']}", file=sys.stderr)
        elif exit_code == 0:
            print("Model data quality OK")
        else:
            print("MODEL DATA QUALITY CHECK FAILED: DATABASE_URL is not set", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the script tests to verify green**

Run: `python -m pytest scripts/tests/test_check_model_data_quality.py -q`
Expected: `7 passed`

- [ ] **Step 6: Run the script itself in safe static mode**

Run: `python scripts/maintenance/check_model_data_quality.py --static-only`
Expected: either `Model data quality OK` or actionable findings from the current repo state. If findings appear, investigate whether they represent real contamination before proceeding.

- [ ] **Step 7: Commit the script and tests**

```bash
git add scripts/maintenance/check_model_data_quality.py scripts/tests/test_check_model_data_quality.py
git commit -m "feat(scripts): add model data quality gate"
```

### Task 3: Wire the quality gate into CI

**Files:**
- Modify: `.github/workflows/ci.yml`
- Test: `scripts/tests/test_check_model_data_quality.py`

- [ ] **Step 1: Add the quality gate step after DB bootstrap in `test-python`**

```yaml
      - name: Bootstrap database
        run: |
          psql "$DATABASE_URL" -f infra/sql/init.sql
          alembic upgrade heads
        env:
          PGPASSWORD: esdata_test

      - name: Run model data quality gate
        run: python scripts/maintenance/check_model_data_quality.py

      - name: Run Python tests
        run: pytest apps/api/tests/ apps/workers/tests/ -v --tb=short
```

- [ ] **Step 2: Run a local lint pass on the touched files**

Run: `python -m ruff check scripts/maintenance/check_model_data_quality.py scripts/tests/test_check_model_data_quality.py`
Expected: `All checks passed!`

- [ ] **Step 3: Commit the CI wiring**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run model data quality gate"
```

### Task 4: Update roadmap and agent notes with fresh verification

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`

- [ ] **Step 1: Add the new agent note for the model data quality gate**

```md
### 2026-05-04 - Fase 3.4 modelos: separar chequeos estaticos de drift persistido

- Scope: `scripts/maintenance/check_model_data_quality.py`, `.github/workflows/ci.yml`, tablas `aeat_modelo` / `modelo_*`
- Hallazgo: los errores peligrosos de `modelos` no nacen solo en runtime. Un hostname no canonico o un mapping debil puede vivir en el source antes de seed, mientras que una fila manual o historica incoherente solo se ve ya persistida en DB.
- Impacto: si el gate mira solo una de las dos superficies, deja escapar justo la mitad del problema: contaminacion preventiva o drift persistido.
- Regla practica: para quality gates de `modelos`, ejecutar siempre chequeos estaticos sobre los scripts canonicos/legacy relevantes y chequeos DB sobre el contrato persistido actual. No confiar en una sola superficie.
```

- [ ] **Step 2: Update the roadmap entry for Fase 3.4 with fresh evidence**

```md
- Nota 2026-05-04 XX:XXZ: Fase 3.4 `[COMPLETA]` cerrada en `G:\_Proyectos\esdata\.worktrees\next-task`. Resultado: `scripts/maintenance/check_model_data_quality.py` introduce un gate pequeno y determinista para detectar hostnames no canonicos, provenance debil en `modelo_articulo`, pseudo-claves sospechosas y drift entre `origen_metadato` / `estado_metadato` en `modelo_campana_operativa`, combinando chequeos estaticos sobre seeds/scripts AEAT y chequeos DB-backed sobre tablas persistidas. `.github/workflows/ci.yml` ejecuta el gate tras `alembic upgrade heads` dentro del job Python con Postgres bootstrappeado. Evidencia fresca: `python -m pytest scripts/tests/test_check_model_data_quality.py -q` -> `7 passed`; `python scripts/maintenance/check_model_data_quality.py --static-only` -> salida verificada; `python -m ruff check scripts/maintenance/check_model_data_quality.py scripts/tests/test_check_model_data_quality.py` -> `All checks passed!`.
```

- [ ] **Step 3: Re-run the full verification for the touched scope**

Run:

```bash
python -m pytest scripts/tests/test_check_model_data_quality.py -q
python scripts/maintenance/check_model_data_quality.py --static-only
python -m ruff check scripts/maintenance/check_model_data_quality.py scripts/tests/test_check_model_data_quality.py
```

Expected:
- `7 passed`
- safe static-only script execution with either `Model data quality OK` or real actionable findings
- `All checks passed!`

- [ ] **Step 4: Commit the docs updates**

```bash
git add docs/master-execution-roadmap.md docs/operations/agent-notes.md
git commit -m "docs: record model data quality gate"
```

## Self-Review

- Spec coverage: this plan covers static checks, DB checks, CLI, exit codes, dedicated tests, CI wiring, and roadmap/agent-notes updates.
- Placeholder scan: no `TODO`/`TBD` placeholders remain in the task steps.
- Type consistency: the plan uses one script entrypoint `run(...)`, one test file, and one CI step consistently across tasks.
