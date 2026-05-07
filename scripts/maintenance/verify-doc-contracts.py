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
