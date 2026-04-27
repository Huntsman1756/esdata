#!/usr/bin/env python
"""Verify docs references and JSON validity for doc artifacts.

Checks that key OpenAPI artifacts referenced from docs exist and contain valid JSON.
Fails fast with a non-zero exit code if any artifact is missing or invalid.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path


def _load_export_module():
    import importlib.util

    module_path = ROOT / "scripts" / "ops" / "export-gpt-openapi.py"
    spec = importlib.util.spec_from_file_location("export_gpt_openapi", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
ARTIFACTS = [
    DOCS_DIR / "openapi-gpt.json",
    DOCS_DIR / "openapi-gpt-3.0.json",
    DOCS_DIR / "openapi-gpt-minimal-modelos.json",
    DOCS_DIR / "openapi-gpt-clipboard.json",
]
ENV_EXAMPLE = ROOT / ".env.example"
ENV_DOC = DOCS_DIR / "environment-variables.md"
DOCS_REFERENCES = [
    DOCS_DIR / "README.md",
    DOCS_DIR / "manual-usuario" / "03-superficies-disponibles.md",
    DOCS_DIR / "manual-usuario" / "06-api-y-ejemplos.md",
    DOCS_DIR / "manual-usuario" / "09-referencia-de-endpoints.md",
    ROOT / "README.md",
]


RELATIVE_LINK_RE = re.compile(r"`?(\.\.?/[^`\s)]+)`?")
ENV_ASSIGNMENT_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=", re.MULTILINE)
DOC_VARIABLE_LINE_RE = re.compile(r"^\|\s*`([A-Z][A-Z0-9_]*)`\s*\|", re.MULTILINE)


def expected_payload_for_artifact(path: Path) -> dict | None:
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ESDATA_API_KEY", "test-secret-key")
    os.environ.setdefault("MCP_API_KEY", "test-mcp-key")
    if "DATABASE_URL" not in os.environ:
        fd, tmp_db_path = tempfile.mkstemp(prefix="esdata_doc_artifacts_", suffix=".sqlite3")
        os.close(fd)
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db_path}"

    export_module = _load_export_module()
    if path.name == "openapi-gpt.json":
        with contextlib.redirect_stdout(io.StringIO()):
            return export_module.export(openapi_version=None, output_path=None)
    if path.name == "openapi-gpt-3.0.json":
        with contextlib.redirect_stdout(io.StringIO()):
            return export_module.export(openapi_version="3.0.3", output_path=None)
    return None


def verify_artifact(path: Path, expected_payload: dict | None = None) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing artifact: {path.relative_to(ROOT)}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid json: {path.relative_to(ROOT)} ({exc})")
        return errors
    if expected_payload is not None and payload != expected_payload:
        errors.append(f"artifact drift: {path.relative_to(ROOT)}")
    return errors


def verify_reference(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing docs file: {path.relative_to(ROOT)}"]
    content = path.read_text(encoding="utf-8")
    for artifact in ARTIFACTS:
        if artifact.name in content and not artifact.exists():
            errors.append(
                f"doc references missing artifact: {path.relative_to(ROOT)} -> {artifact.relative_to(ROOT)}"
            )
    for match in RELATIVE_LINK_RE.findall(content):
        target = (path.parent / match).resolve()
        if not target.exists():
            errors.append(f"broken relative link: {path.relative_to(ROOT)} -> {match}")
    return errors


def extract_env_example_variables(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {match.group(1) for match in ENV_ASSIGNMENT_RE.finditer(path.read_text(encoding="utf-8"))}


def extract_documented_variables(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {match.group(1) for match in DOC_VARIABLE_LINE_RE.finditer(path.read_text(encoding="utf-8"))}


def verify_env_documentation(env_example: Path, env_doc: Path) -> list[str]:
    errors: list[str] = []
    env_variables = extract_env_example_variables(env_example)
    documented_variables = extract_documented_variables(env_doc)

    missing_in_docs = sorted(env_variables - documented_variables)
    missing_in_example = sorted(documented_variables - env_variables)

    for variable in missing_in_docs:
        errors.append(f"env drift: missing in docs/environment-variables.md: {variable}")
    for variable in missing_in_example:
        errors.append(f"env drift: missing in .env.example: {variable}")

    return errors


def find_forbidden_env_files(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.rglob(".env*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        relative_posix = relative.as_posix()
        if relative.name == ".env.example":
            continue
        if relative_posix.startswith(".worktrees/"):
            continue
        if relative_posix.startswith("scripts/tests/.tmp_verify_doc_artifacts/"):
            continue
        findings.append(relative_posix)
    return findings


def run() -> list[str]:
    errors: list[str] = []
    for artifact in ARTIFACTS:
        errors.extend(verify_artifact(artifact, expected_payload=expected_payload_for_artifact(artifact)))
    for doc in DOCS_REFERENCES:
        errors.extend(verify_reference(doc))
    errors.extend(verify_env_documentation(ENV_EXAMPLE, ENV_DOC))
    for forbidden in find_forbidden_env_files(ROOT):
        errors.append(f"forbidden env file: {forbidden}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify docs artifacts referenced by the repo")
    parser.parse_args()
    errors = run()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("docs artifacts verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
