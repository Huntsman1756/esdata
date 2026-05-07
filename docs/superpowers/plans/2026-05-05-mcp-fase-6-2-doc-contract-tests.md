# MCP Fase 6.2 Doc Contract Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small script-based documentation contract gate that freezes the `6.1` boundaries between `REST/OpenAPI`, `HTTP MCP`, `stdio MCP`, and the `OpenCode -> HTTP MCP` guide.

**Architecture:** Keep `6.2` entirely in `scripts/`. Implement one Python verifier in `scripts/maintenance/verify-doc-contracts.py`, back it with focused tests in `scripts/tests/test_verify_doc_contracts.py`, and use roadmap bookkeeping to claim and close the phase with fresh verification evidence.

**Tech Stack:** Python, `pathlib`, `argparse`, `pytest`, markdown token checks

---

## File Map

- Modify: `docs/master-execution-roadmap.md`
  Claim `6.2` before implementation and close it with fresh evidence after the gate passes.
- Create: `scripts/maintenance/verify-doc-contracts.py`
  Small verifier with one validator per guarded doc plus a `run()`/`main()` entrypoint.
- Create: `scripts/tests/test_verify_doc_contracts.py`
  Pure tests that dynamically import the verifier, point it at temp docs, and assert both passing and failing contract cases.

### Task 1: Claim `Fase 6.2` in the roadmap

**Files:**
- Modify: `docs/master-execution-roadmap.md`

- [ ] **Step 1: Read the live summary block before editing**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: the block still shows `Fase 6.1` closed, no active claim, and `Fase 6.2` as the next step pending confirmation.

- [ ] **Step 2: Update the summary to mark `6.2` as in progress**

Replace the live-summary bullets with this target structure:

```md
- Objetivo actual: ejecutar **Fase 6.2** del plan MCP para anadir tests de contrato documental sobre las superficies y guias ya alineadas.
- Estado actual: **Fase 5.5** `[COMPLETA]` y **Fase 6.1** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; **Fase 6.2** `[EN CURSO]` anade un gate pequeno en `scripts/` para fijar la separacion entre `REST/OpenAPI`, `HTTP MCP`, `stdio MCP` y el scope `OpenCode -> HTTP MCP`.
- Estado del agente activo: diseno y spec de `6.2` aprobados; implementacion del gate documental en curso con un script dedicado y tests puros en `scripts/tests/`.
- Reclamo actual: **Fase 6.2** `[EN CURSO]` — archivos reclamados: `docs/master-execution-roadmap.md`, `scripts/maintenance/verify-doc-contracts.py`, `scripts/tests/test_verify_doc_contracts.py`, `docs/superpowers/specs/2026-05-05-mcp-fase-6-2-doc-contract-tests-design.md`, `docs/superpowers/plans/2026-05-05-mcp-fase-6-2-doc-contract-tests.md`. Inicio: 2026-05-05.
- Siguiente paso exacto: escribir el test fallando para el gate documental, implementar el verificador minimo en `scripts/maintenance/verify-doc-contracts.py` y validarlo con `python -m pytest scripts/tests/test_verify_doc_contracts.py -q` y `python scripts/maintenance/verify-doc-contracts.py`.
```

- [ ] **Step 3: Read back the updated summary**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: the block now shows `Fase 6.2` as `[EN CURSO]` with the new claim and exact next step.

- [ ] **Step 4: Commit**

```bash
git add docs/master-execution-roadmap.md
git commit -m "docs(roadmap): claim mcp phase 6.2"
```

### Task 2: Write the first failing tests and implement the minimal gate

**Files:**
- Create: `scripts/tests/test_verify_doc_contracts.py`
- Create: `scripts/maintenance/verify-doc-contracts.py`
- Test: `scripts/tests/test_verify_doc_contracts.py`

- [ ] **Step 1: Write failing tests for `architecture` and chapter `06`**

Create `scripts/tests/test_verify_doc_contracts.py` with this initial content:

```python
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "maintenance" / "verify-doc-contracts.py"
TEST_TMP_ROOT = Path(__file__).resolve().parent / ".tmp_verify_doc_contracts"

VALID_ARCHITECTURE = """## Superficies de integracion activas
REST/OpenAPI
HTTP MCP
stdio MCP
"""

VALID_MANUAL_06 = """# API y ejemplos
La integracion MCP se documenta aparte en `07-mcp-y-clientes.md`.
Este capitulo se limita a `REST/OpenAPI`.
"""

VALID_MANUAL_07 = """# MCP y clientes
apps/api/mcp_catalog.py
HTTP_MCP_OPERATIONS
apps/api/mcp_stdio.py
consulta_fiscal
"""

VALID_OPENCODE = """# OpenCode + HTTP MCP
OpenCode
HTTP MCP
/mcp
X-API-Key: <MCP_API_KEY>
No cubre `stdio MCP`
"""


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_doc_contracts", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _reset_tmp_dir() -> Path:
    if TEST_TMP_ROOT.exists():
        shutil.rmtree(TEST_TMP_ROOT)
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return TEST_TMP_ROOT


def _write_docs(
    base: Path,
    *,
    architecture: str = VALID_ARCHITECTURE,
    manual06: str = VALID_MANUAL_06,
    manual07: str = VALID_MANUAL_07,
    opencode: str = VALID_OPENCODE,
) -> None:
    docs_dir = base / "docs"
    (docs_dir / "manual-usuario").mkdir(parents=True, exist_ok=True)
    (docs_dir / "integrations").mkdir(parents=True, exist_ok=True)
    (docs_dir / "architecture.md").write_text(architecture, encoding="utf-8")
    (docs_dir / "manual-usuario" / "06-api-y-ejemplos.md").write_text(manual06, encoding="utf-8")
    (docs_dir / "manual-usuario" / "07-mcp-y-clientes.md").write_text(manual07, encoding="utf-8")
    (docs_dir / "integrations" / "opencode-local-and-vps.md").write_text(opencode, encoding="utf-8")


def _configure_module_paths(module, base: Path) -> None:
    module.ROOT = base
    module.DOCS_DIR = base / "docs"
    module.ARCHITECTURE_DOC = module.DOCS_DIR / "architecture.md"
    module.MANUAL_API_DOC = module.DOCS_DIR / "manual-usuario" / "06-api-y-ejemplos.md"
    module.MANUAL_MCP_DOC = module.DOCS_DIR / "manual-usuario" / "07-mcp-y-clientes.md"
    module.OPENCODE_DOC = module.DOCS_DIR / "integrations" / "opencode-local-and-vps.md"


def test_verify_architecture_contract_accepts_three_surface_split():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir)
    _configure_module_paths(module, tmp_dir)

    assert module.verify_architecture_contract() == []


def test_verify_architecture_contract_reports_missing_surface():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir, architecture="REST/OpenAPI\nHTTP MCP\n")
    _configure_module_paths(module, tmp_dir)

    assert module.verify_architecture_contract() == [
        "docs contract drift: architecture missing stdio MCP"
    ]


def test_verify_manual_api_contract_accepts_rest_only_chapter():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir)
    _configure_module_paths(module, tmp_dir)

    assert module.verify_manual_api_contract() == []


def test_verify_manual_api_contract_reports_mcp_drift():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir, manual06="# API y ejemplos\n/mcp\n")
    _configure_module_paths(module, tmp_dir)

    assert module.verify_manual_api_contract() == [
        "docs contract drift: manual 06 mentions /mcp"
    ]
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
python -m pytest scripts/tests/test_verify_doc_contracts.py -q -k "architecture or manual_api"
```

Expected: FAIL because `scripts/maintenance/verify-doc-contracts.py` does not exist yet and the dynamic import raises a file-loading error.

- [ ] **Step 3: Write the minimal verifier for the first two contracts**

Create `scripts/maintenance/verify-doc-contracts.py` with this initial content:

```python
#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
ARCHITECTURE_DOC = DOCS_DIR / "architecture.md"
MANUAL_API_DOC = DOCS_DIR / "manual-usuario" / "06-api-y-ejemplos.md"
MANUAL_MCP_DOC = DOCS_DIR / "manual-usuario" / "07-mcp-y-clientes.md"
OPENCODE_DOC = DOCS_DIR / "integrations" / "opencode-local-and-vps.md"


def _missing_file_error(path: Path) -> list[str]:
    if path.exists():
        return []
    return [f"docs contract drift: missing file {path.relative_to(ROOT)}"]


def verify_architecture_contract() -> list[str]:
    errors = _missing_file_error(ARCHITECTURE_DOC)
    if errors:
        return errors

    content = ARCHITECTURE_DOC.read_text(encoding="utf-8")
    for token in ("REST/OpenAPI", "HTTP MCP", "stdio MCP"):
        if token not in content:
            errors.append(f"docs contract drift: architecture missing {token}")
    return errors


def verify_manual_api_contract() -> list[str]:
    errors = _missing_file_error(MANUAL_API_DOC)
    if errors:
        return errors

    content = MANUAL_API_DOC.read_text(encoding="utf-8")
    if "/mcp" in content:
        errors.append("docs contract drift: manual 06 mentions /mcp")
    return errors


def verify_manual_mcp_contract() -> list[str]:
    errors = _missing_file_error(MANUAL_MCP_DOC)
    if errors:
        return errors
    return []


def verify_opencode_contract() -> list[str]:
    errors = _missing_file_error(OPENCODE_DOC)
    if errors:
        return errors
    return []


def run() -> list[str]:
    errors: list[str] = []
    errors.extend(verify_architecture_contract())
    errors.extend(verify_manual_api_contract())
    errors.extend(verify_manual_mcp_contract())
    errors.extend(verify_opencode_contract())
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MCP documentation contracts")
    parser.parse_args()
    errors = run()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("docs contracts verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the selected tests again to verify the minimal gate passes**

Run:

```bash
python -m pytest scripts/tests/test_verify_doc_contracts.py -q -k "architecture or manual_api"
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/maintenance/verify-doc-contracts.py scripts/tests/test_verify_doc_contracts.py
git commit -m "test(docs): add initial doc contract gate"
```

### Task 3: Extend the gate to chapter `07`, `OpenCode`, and aggregated failures

**Files:**
- Modify: `scripts/tests/test_verify_doc_contracts.py`
- Modify: `scripts/maintenance/verify-doc-contracts.py`
- Test: `scripts/tests/test_verify_doc_contracts.py`

- [ ] **Step 1: Expand the tests to cover chapter `07`, `OpenCode`, and `run()` aggregation**

Replace `scripts/tests/test_verify_doc_contracts.py` with this full content:

```python
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "maintenance" / "verify-doc-contracts.py"
TEST_TMP_ROOT = Path(__file__).resolve().parent / ".tmp_verify_doc_contracts"

VALID_ARCHITECTURE = """## Superficies de integracion activas
REST/OpenAPI
HTTP MCP
stdio MCP
"""

VALID_MANUAL_06 = """# API y ejemplos
La integracion MCP se documenta aparte en `07-mcp-y-clientes.md`.
Este capitulo se limita a `REST/OpenAPI`.
"""

VALID_MANUAL_07 = """# MCP y clientes
apps/api/mcp_catalog.py
HTTP_MCP_OPERATIONS
apps/api/mcp_stdio.py
consulta_fiscal
"""

VALID_OPENCODE = """# OpenCode + HTTP MCP
OpenCode
HTTP MCP
/mcp
X-API-Key: <MCP_API_KEY>
No cubre `stdio MCP`
"""


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_doc_contracts", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _reset_tmp_dir() -> Path:
    if TEST_TMP_ROOT.exists():
        shutil.rmtree(TEST_TMP_ROOT)
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return TEST_TMP_ROOT


def _write_docs(
    base: Path,
    *,
    architecture: str = VALID_ARCHITECTURE,
    manual06: str = VALID_MANUAL_06,
    manual07: str = VALID_MANUAL_07,
    opencode: str = VALID_OPENCODE,
) -> None:
    docs_dir = base / "docs"
    (docs_dir / "manual-usuario").mkdir(parents=True, exist_ok=True)
    (docs_dir / "integrations").mkdir(parents=True, exist_ok=True)
    (docs_dir / "architecture.md").write_text(architecture, encoding="utf-8")
    (docs_dir / "manual-usuario" / "06-api-y-ejemplos.md").write_text(manual06, encoding="utf-8")
    (docs_dir / "manual-usuario" / "07-mcp-y-clientes.md").write_text(manual07, encoding="utf-8")
    (docs_dir / "integrations" / "opencode-local-and-vps.md").write_text(opencode, encoding="utf-8")


def _configure_module_paths(module, base: Path) -> None:
    module.ROOT = base
    module.DOCS_DIR = base / "docs"
    module.ARCHITECTURE_DOC = module.DOCS_DIR / "architecture.md"
    module.MANUAL_API_DOC = module.DOCS_DIR / "manual-usuario" / "06-api-y-ejemplos.md"
    module.MANUAL_MCP_DOC = module.DOCS_DIR / "manual-usuario" / "07-mcp-y-clientes.md"
    module.OPENCODE_DOC = module.DOCS_DIR / "integrations" / "opencode-local-and-vps.md"


def test_verify_architecture_contract_accepts_three_surface_split():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir)
    _configure_module_paths(module, tmp_dir)

    assert module.verify_architecture_contract() == []


def test_verify_architecture_contract_reports_missing_surface():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir, architecture="REST/OpenAPI\nHTTP MCP\n")
    _configure_module_paths(module, tmp_dir)

    assert module.verify_architecture_contract() == [
        "docs contract drift: architecture missing stdio MCP"
    ]


def test_verify_manual_api_contract_accepts_rest_only_chapter():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir)
    _configure_module_paths(module, tmp_dir)

    assert module.verify_manual_api_contract() == []


def test_verify_manual_api_contract_reports_mcp_drift():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir, manual06="# API y ejemplos\n/mcp\n")
    _configure_module_paths(module, tmp_dir)

    assert module.verify_manual_api_contract() == [
        "docs contract drift: manual 06 mentions /mcp"
    ]


def test_verify_manual_mcp_contract_accepts_required_anchors():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir)
    _configure_module_paths(module, tmp_dir)

    assert module.verify_manual_mcp_contract() == []


def test_verify_manual_mcp_contract_reports_missing_anchor():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir, manual07="# MCP y clientes\napps/api/mcp_catalog.py\napps/api/mcp_stdio.py\nconsulta_fiscal\n")
    _configure_module_paths(module, tmp_dir)

    assert module.verify_manual_mcp_contract() == [
        "docs contract drift: chapter 07 missing HTTP_MCP_OPERATIONS reference"
    ]


def test_verify_opencode_contract_accepts_http_only_guide():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir)
    _configure_module_paths(module, tmp_dir)

    assert module.verify_opencode_contract() == []


def test_verify_opencode_contract_reports_missing_api_key_anchor():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir, opencode="# OpenCode + HTTP MCP\nOpenCode\nHTTP MCP\n/mcp\nNo cubre `stdio MCP`\n")
    _configure_module_paths(module, tmp_dir)

    assert module.verify_opencode_contract() == [
        "docs contract drift: opencode guide missing X-API-Key: <MCP_API_KEY> reference"
    ]


def test_verify_opencode_contract_reports_missing_stdio_scope_boundary():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(tmp_dir, opencode="# OpenCode + HTTP MCP\nOpenCode\nHTTP MCP\n/mcp\nX-API-Key: <MCP_API_KEY>\n")
    _configure_module_paths(module, tmp_dir)

    assert module.verify_opencode_contract() == [
        "docs contract drift: opencode guide missing stdio-out-of-scope note"
    ]


def test_run_aggregates_findings_across_multiple_docs():
    module = _load_module()
    tmp_dir = _reset_tmp_dir()
    _write_docs(
        tmp_dir,
        architecture="REST/OpenAPI\nHTTP MCP\n",
        manual06="# API y ejemplos\n/mcp\n",
        manual07="# MCP y clientes\napps/api/mcp_catalog.py\napps/api/mcp_stdio.py\nconsulta_fiscal\n",
        opencode="# OpenCode + HTTP MCP\nOpenCode\nHTTP MCP\n/mcp\n",
    )
    _configure_module_paths(module, tmp_dir)

    assert module.run() == [
        "docs contract drift: architecture missing stdio MCP",
        "docs contract drift: manual 06 mentions /mcp",
        "docs contract drift: chapter 07 missing HTTP_MCP_OPERATIONS reference",
        "docs contract drift: opencode guide missing X-API-Key: <MCP_API_KEY> reference",
        "docs contract drift: opencode guide missing stdio-out-of-scope note",
    ]
```

- [ ] **Step 2: Run the new subset to verify the remaining contract checks fail first**

Run:

```bash
python -m pytest scripts/tests/test_verify_doc_contracts.py -q -k "manual_mcp or opencode or aggregates"
```

Expected: `4 failed, 2 passed, 4 deselected` because `verify_manual_mcp_contract()` and `verify_opencode_contract()` still return empty findings.

- [ ] **Step 3: Finish the verifier for chapter `07` and the `OpenCode` guide**

Replace `scripts/maintenance/verify-doc-contracts.py` with this full content:

```python
#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
ARCHITECTURE_DOC = DOCS_DIR / "architecture.md"
MANUAL_API_DOC = DOCS_DIR / "manual-usuario" / "06-api-y-ejemplos.md"
MANUAL_MCP_DOC = DOCS_DIR / "manual-usuario" / "07-mcp-y-clientes.md"
OPENCODE_DOC = DOCS_DIR / "integrations" / "opencode-local-and-vps.md"


def _missing_file_error(path: Path) -> list[str]:
    if path.exists():
        return []
    return [f"docs contract drift: missing file {path.relative_to(ROOT)}"]


def verify_architecture_contract() -> list[str]:
    errors = _missing_file_error(ARCHITECTURE_DOC)
    if errors:
        return errors

    content = ARCHITECTURE_DOC.read_text(encoding="utf-8")
    for token in ("REST/OpenAPI", "HTTP MCP", "stdio MCP"):
        if token not in content:
            errors.append(f"docs contract drift: architecture missing {token}")
    return errors


def verify_manual_api_contract() -> list[str]:
    errors = _missing_file_error(MANUAL_API_DOC)
    if errors:
        return errors

    content = MANUAL_API_DOC.read_text(encoding="utf-8")
    if "/mcp" in content:
        errors.append("docs contract drift: manual 06 mentions /mcp")
    return errors


def verify_manual_mcp_contract() -> list[str]:
    errors = _missing_file_error(MANUAL_MCP_DOC)
    if errors:
        return errors

    content = MANUAL_MCP_DOC.read_text(encoding="utf-8")
    required_tokens = {
        "apps/api/mcp_catalog.py": "apps/api/mcp_catalog.py reference",
        "HTTP_MCP_OPERATIONS": "HTTP_MCP_OPERATIONS reference",
        "apps/api/mcp_stdio.py": "apps/api/mcp_stdio.py reference",
        "consulta_fiscal": "consulta_fiscal reference",
    }
    for token, label in required_tokens.items():
        if token not in content:
            errors.append(f"docs contract drift: chapter 07 missing {label}")
    return errors


def verify_opencode_contract() -> list[str]:
    errors = _missing_file_error(OPENCODE_DOC)
    if errors:
        return errors

    content = OPENCODE_DOC.read_text(encoding="utf-8")
    required_tokens = {
        "OpenCode": "OpenCode reference",
        "HTTP MCP": "HTTP MCP reference",
        "/mcp": "/mcp reference",
        "X-API-Key: <MCP_API_KEY>": "X-API-Key: <MCP_API_KEY> reference",
    }
    for token, label in required_tokens.items():
        if token not in content:
            errors.append(f"docs contract drift: opencode guide missing {label}")

    if "stdio MCP" not in content and "No cubre" not in content:
        errors.append("docs contract drift: opencode guide missing stdio-out-of-scope note")
    return errors


def run() -> list[str]:
    errors: list[str] = []
    errors.extend(verify_architecture_contract())
    errors.extend(verify_manual_api_contract())
    errors.extend(verify_manual_mcp_contract())
    errors.extend(verify_opencode_contract())
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MCP documentation contracts")
    parser.parse_args()
    errors = run()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("docs contracts verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the full test file to verify the contract suite passes**

Run:

```bash
python -m pytest scripts/tests/test_verify_doc_contracts.py -q
```

Expected: `10 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/maintenance/verify-doc-contracts.py scripts/tests/test_verify_doc_contracts.py
git commit -m "test(docs): finish mcp doc contract checks"
```

### Task 4: Run the gate on the live docs and close `Fase 6.2`

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Test: `scripts/tests/test_verify_doc_contracts.py`
- Test: `scripts/maintenance/verify-doc-contracts.py`

- [ ] **Step 1: Run the fresh verification evidence for the phase**

Run:

```bash
python -m pytest scripts/tests/test_verify_doc_contracts.py -q
python scripts/maintenance/verify-doc-contracts.py
```

Expected:

- first command prints `10 passed`
- second command prints `docs contracts verified`

- [ ] **Step 2: Read the live roadmap summary before closing the phase**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: `Fase 6.2` is still `[EN CURSO]` and the active claim names the script and test file.

- [ ] **Step 3: Update the summary and add a historical closeout note**

Replace the live-summary bullets with this target structure:

```md
- Objetivo actual: preparar **Fase 6.3** del plan MCP para crear el checklist go/no-go de release.
- Estado actual: **Fase 5.5** `[COMPLETA]`, **Fase 6.1** `[COMPLETA]` y **Fase 6.2** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; el repo ya tiene un gate pequeno para detectar drift en la separacion documental entre `REST/OpenAPI`, `HTTP MCP`, `stdio MCP` y `OpenCode -> HTTP MCP`.
- Estado del agente activo: cierre de `6.2` completado con evidencia fresca; no hay nueva fase reclamada y pasar a `6.3` requiere confirmacion explicita del usuario.
- Reclamo actual: ninguno. **Fase 6.2** queda cerrada; archivos afectados en el slice: `docs/master-execution-roadmap.md`, `scripts/maintenance/verify-doc-contracts.py`, `scripts/tests/test_verify_doc_contracts.py`.
- Siguiente paso exacto: esperar confirmacion del usuario y, si la da, reclamar y ejecutar **Fase 6.3 — Crear checklist go/no-go para release MCP**.
```

Add this historical note near the top of `### Historial MCP [HISTORICAL]`:

```md
- Nota 2026-05-05: Fase 6.2 `[COMPLETA]` cerrada en `G:\_Proyectos\esdata\.worktrees\next-task`. Resultado: `scripts/maintenance/verify-doc-contracts.py` fija un gate pequeno para la separacion documental entre `REST/OpenAPI`, `HTTP MCP`, `stdio MCP` y la guia `OpenCode -> HTTP MCP`; `scripts/tests/test_verify_doc_contracts.py` cubre contratos validos y drift representativo con temp docs aislados; y la verificacion local del slice ya falla si `06` vuelve a mencionar `/mcp`, si `07` pierde anchors como `apps/api/mcp_catalog.py` o `HTTP_MCP_OPERATIONS`, o si la guia de `OpenCode` pierde `X-API-Key: <MCP_API_KEY>` o el boundary de `stdio`. Evidencia fresca del cierre: `python -m pytest scripts/tests/test_verify_doc_contracts.py -q` -> `10 passed`; `python scripts/maintenance/verify-doc-contracts.py` -> `docs contracts verified`. Riesgo residual explicitado: el gate queda listo para uso local y para cableado posterior en CI, pero `6.2` no anade todavia workflow automation ni snapshots documentales mas estrictos; eso queda fuera del slice.
```

- [ ] **Step 4: Read back the updated summary and historical note**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:242], start=217)))"
```

Expected: `Fase 6.2` reads as complete, there is no active claim, and `Fase 6.3` is the only next step.

- [ ] **Step 5: Commit**

```bash
git add docs/master-execution-roadmap.md
git commit -m "docs(roadmap): close mcp phase 6.2"
```

## Self-Review Checklist

- Spec coverage: the plan claims and closes `6.2`, creates the verifier script, creates the dedicated tests, and records fresh evidence in the roadmap.
- Placeholder scan: there are no `TODO`, `TBD`, or "similar to" instructions; every task names exact files, commands, and expected outcomes.
- Type consistency: the function names used by the tests (`verify_architecture_contract`, `verify_manual_api_contract`, `verify_manual_mcp_contract`, `verify_opencode_contract`, `run`) match the verifier implementation exactly.
