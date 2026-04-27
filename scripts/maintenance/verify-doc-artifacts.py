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


def verify_docs_vs_roadmap() -> list[str]:
    """Verify that docs don't claim implemented state for target-state features.

    Checks master-execution-roadmap.md for [PARTIAL] or [TARGET] markers and
    cross-references docs to ensure they don't describe those features as [IMPLEMENTED].
    """
    errors: list[str] = []
    roadmap_path = DOCS_DIR / "master-execution-roadmap.md"
    if not roadmap_path.exists():
        return errors

    roadmap_content = roadmap_path.read_text(encoding="utf-8")

    # Find features marked as [PARTIAL] or [TARGET] in the roadmap
    partial_target_features = set(re.findall(r"\[(?:PARTIAL|TARGET)\]", roadmap_content))
    if not partial_target_features:
        return errors

    # Check docs for claims of these features being fully implemented
    for doc_path in DOCS_DIR.rglob("*.md"):
        if "archive" in doc_path.parts or "manual-usuario" in doc_path.parts:
            continue
        doc_content = doc_path.read_text(encoding="utf-8")
        # Look for overly confident claims about features that are still partial/target
        for feature_marker in partial_target_features:
            # If docs claim something is implemented but roadmap says partial/target
            if "[IMPLEMENTED]" in doc_content and feature_marker:
                # Only flag if the same section/topic appears in both
                doc_topic = doc_path.relative_to(DOCS_DIR).with_suffix("")
                if doc_topic.as_posix() in roadmap_content:
                    errors.append(
                        f"docs drift: {doc_path.relative_to(ROOT)} claims [IMPLEMENTED] "
                        f"but roadmap has {feature_marker} for overlapping topic "
                        f"'{doc_topic}'"
                    )

    return errors


def verify_workers_documented() -> list[str]:
    """Verify that all workers in apps/workers/ are referenced in docs."""
    errors: list[str] = []
    workers_dir = ROOT / "apps" / "workers"
    if not workers_dir.exists():
        return errors

    # Find worker modules (excluding __pycache__, __init__, tests, shared modules)
    worker_modules = set()
    for py_file in workers_dir.glob("*.py"):
        name = py_file.stem
        if name.startswith("_") or name in ("embeddings", "entity_identity", "db", "base"):
            continue
        if name.startswith("test_"):
            continue
        worker_modules.add(name)

    if not worker_modules:
        return errors

    # Check docs for worker references
    docs_content = ""
    for doc_path in DOCS_DIR.rglob("*.md"):
        docs_content += doc_path.read_text(encoding="utf-8") + "\n"

    # Check manual-usuario specifically
    manual_dir = DOCS_DIR / "manual-usuario"
    if manual_dir.exists():
        manual_content = ""
        for doc_path in manual_dir.rglob("*.md"):
            manual_content += doc_path.read_text(encoding="utf-8") + "\n"
    else:
        manual_content = ""

    undocumented = sorted(worker_modules - {w for w in worker_modules if w in docs_content})
    if undocumented:
        errors.append(
            f"undocumented workers ({len(undocumented)}): {', '.join(undocumented[:10])}"
        )

    return errors


def verify_endpoints_documented() -> list[str]:
    """Verify that API router endpoints are referenced in docs."""
    errors: list[str] = []
    routers_dir = ROOT / "apps" / "api" / "routers"
    if not routers_dir.exists():
        return errors

    # Find router files
    router_files = list(routers_dir.glob("*.py"))
    if not router_files:
        return errors

    # Extract endpoint paths from router files
    endpoint_paths = set()
    for router_file in router_files:
        content = router_file.read_text(encoding="utf-8")
        for match in re.finditer(r'@(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', content):
            endpoint_paths.add(match.group(1))

    if not endpoint_paths:
        return errors

    # Check docs for endpoint references
    docs_content = ""
    for doc_path in DOCS_DIR.rglob("*.md"):
        docs_content += doc_path.read_text(encoding="utf-8") + "\n"

    undocumented = sorted(p for p in endpoint_paths if "/" not in p or p not in docs_content)
    if len(undocumented) > len(endpoint_paths) * 0.3:
        errors.append(
            f"undocumented endpoints ({len(undocumented)}/{len(endpoint_paths)}): "
            f"more than 30% of endpoints not referenced in docs"
        )

    return errors


def run() -> list[str]:
    errors: list[str] = []
    for artifact in ARTIFACTS:
        errors.extend(verify_artifact(artifact, expected_payload=expected_payload_for_artifact(artifact)))
    for doc in DOCS_REFERENCES:
        errors.extend(verify_reference(doc))
    errors.extend(verify_env_documentation(ENV_EXAMPLE, ENV_DOC))
    for forbidden in find_forbidden_env_files(ROOT):
        errors.append(f"forbidden env file: {forbidden}")
    errors.extend(verify_docs_vs_roadmap())
    errors.extend(verify_workers_documented())
    errors.extend(verify_endpoints_documented())
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
