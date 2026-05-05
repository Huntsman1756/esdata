from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest


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


@pytest.fixture(autouse=True)
def _cleanup_tmp_dir():
    if TEST_TMP_ROOT.exists():
        shutil.rmtree(TEST_TMP_ROOT)
    yield
    if TEST_TMP_ROOT.exists():
        shutil.rmtree(TEST_TMP_ROOT)


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
