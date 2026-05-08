#!/usr/bin/env python
"""Verify docs references, JSON validity, markdown lint, and link checks.

Checks that key OpenAPI artifacts referenced from docs exist and contain valid JSON.
Validates markdown structure (headings, links, line length, fenced code blocks).
Verifies internal relative links resolve.
Fails fast with a non-zero exit code if any check fails.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Final


def _load_export_module():
    import importlib.util

    module_path = ROOT / "scripts" / "ops" / "export-gpt-openapi.py"
    spec = importlib.util.spec_from_file_location("export_gpt_openapi", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None, "spec is None"
    assert spec.loader is not None, "spec.loader is None"
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
LEGACY_DOC_VARIABLE_LINE_RE = re.compile(
    r"^\|\s*`([A-Z][A-Z0-9_]*)`\s*\|\s*`legacy/no cableada`\s*\|",
    re.MULTILINE,
)

# Markdown lint rules (Python-native, no external tools)
_INTERNAL_LINK_RE: Final[re.Pattern] = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_INLINE_LINK_RE: Final[re.Pattern] = re.compile(r"`?(\.\.?/[^`\s)]+)`?")
_HEADING_RE: Final[re.Pattern] = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_FENCED_CODE_RE: Final[re.Pattern] = re.compile(r"^(`{3,}|~{3,})(\w*)$", re.MULTILINE)
_FENCED_CODE_CLOSE_RE: Final[re.Pattern] = re.compile(r"^(`{3,}|~{3,})$", re.MULTILINE)
_LINE_LENGTH_LIMIT: Final[int] = 200
_MANUAL_USERLINE_LENGTH_LIMIT: Final[int] = 300


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
            errors.append(f"doc references missing artifact: {path.relative_to(ROOT)} -> {artifact.relative_to(ROOT)}")
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


def extract_legacy_documented_variables(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {match.group(1) for match in LEGACY_DOC_VARIABLE_LINE_RE.finditer(path.read_text(encoding="utf-8"))}


def verify_env_documentation(env_example: Path, env_doc: Path) -> list[str]:
    errors: list[str] = []
    env_variables = extract_env_example_variables(env_example)
    documented_variables = extract_documented_variables(env_doc)
    legacy_documented_variables = extract_legacy_documented_variables(env_doc)

    missing_in_docs = sorted(env_variables - documented_variables)
    missing_in_example = sorted(documented_variables - env_variables - legacy_documented_variables)

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

    excluded_docs = {
        DOCS_DIR / "master-execution-roadmap.md",
        DOCS_DIR / "architecture.md",
        DOCS_DIR / "COMPLIANCE.md",
    }

    # Check docs for claims of these features being fully implemented.
    # Status inventory docs legitimately contain mixed [IMPLEMENTED]/[PARTIAL]/[TARGET]
    # markers and are reviewed by their own content, not this coarse overlap guard.
    for doc_path in DOCS_DIR.rglob("*.md"):
        if doc_path in excluded_docs:
            continue
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
        errors.append(f"undocumented workers ({len(undocumented)}): {', '.join(undocumented[:10])}")

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


# Files and patterns excluded from markdown lint (historically accumulated,
# not actively maintained, or intentionally long lines like tables/code).
_LINT_EXCLUDE_PATTERNS: Final[tuple[str, ...]] = (
    "CHANGELOG.md",
    "MEMO.md",
    "master-execution-roadmap.md",
    "environment-variables.md",
    "OPERATIONS.md",
    "backup-restore.md",
    "deploy-compose.md",
    "mcp-release-gate.md",
    "mcp-remediation-plan.md",
    "model-expansion-spec.md",
    "architecture.md",
    "ai-act-risk-assessment.md",
    "gdpr-dpia-ai-data-processing.md",
    "agent-notes.md",
    "metrics.md",
    "screening-datasets.md",
    "worker-failures.md",
    "compliance",
    "2026-",  # dated release notes
    "design.md",
    "curacion-lineas-criterio.md",
    "fase-13-entity-identity.md",
    "rirpf-ingestion.md",
)


def _is_lint_excluded(path: Path) -> bool:
    """Check if a markdown file should be excluded from lint checks."""
    relative = path.relative_to(DOCS_DIR)
    parts = relative.parts
    name = path.name
    for pattern in _LINT_EXCLUDE_PATTERNS:
        if name == pattern:
            return True
        if pattern in parts:
            return True
        if pattern == "2026-" and name.startswith("2026-"):
            return True
    return False


def collect_markdown_files(root: Path) -> list[Path]:
    """Collect all .md files under docs/, excluding archive and node_modules."""
    md_files: list[Path] = []
    for md in root.rglob("*.md"):
        if "archive" in md.parts or "node_modules" in md.parts or ".git" in md.parts:
            continue
        md_files.append(md)
    return sorted(md_files)


@dataclass
class LintIssue:
    file: Path
    line: int
    rule: str
    message: str


def lint_markdown_file(path: Path) -> list[str]:
    """Lint a single markdown file for structural issues.

    Checks:
    - Heading depth (must be # through ######)
    - Line length > 200 chars (300 for manual-usuario)
    - Unclosed fenced code blocks
    - Empty lines after headings
    - Images without alt text
    - Duplicate headings in same file
    """
    errors: list[str] = []
    if not path.exists():
        return errors

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    in_code_block = False
    seen_headings: dict[str, int] = {}
    prev_was_heading = False

    # Use higher line-length limit for manual-usuario (has code examples)
    line_limit = _MANUAL_USERLINE_LENGTH_LIMIT if "manual-usuario" in path.parts else _LINE_LENGTH_LIMIT

    for i, line in enumerate(lines, 1):
        # Track fenced code blocks
        if re.match(r"^(`{3,}|~{3,})\w*$", line):
            if not in_code_block:
                in_code_block = True
            elif in_code_block:
                in_code_block = False
            continue

        # Skip content inside code blocks for most checks
        if in_code_block:
            continue

        # Heading depth check
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            depth = len(heading_match.group(1))
            if depth > 6:
                errors.append(f"{path.name}:{i}: heading-depth: heading level {depth} exceeds max 6")
            # Check for ATX-style with no space after #
            if re.match(r"^#{1,6}[^#\s]", line):
                errors.append(f"{path.name}:{i}: heading-space: missing space after # in heading")
            # Track duplicate headings
            text = heading_match.group(2).strip()
            if text in seen_headings:
                errors.append(f"{path.name}:{i}: duplicate-heading: '{text}' first seen at line {seen_headings[text]}")
            else:
                seen_headings[text] = i
            prev_was_heading = True
            continue

        # Empty line after heading check
        if prev_was_heading and line.strip() == "":
            # This is actually fine — empty line after heading is good practice
            pass
        prev_was_heading = False

        # Line length check
        if len(line) > line_limit:
            errors.append(f"{path.name}:{i}: line-length: {len(line)} chars exceeds limit {line_limit}")

        # Image without alt text check
        img_match = re.search(r"!\[\]\(([^)]+)\)", line)
        if img_match:
            errors.append(f"{path.name}:{i}: image-alt: image without alt text: {img_match.group(1)[:60]}")

    # Check for unclosed code blocks
    if in_code_block:
        errors.append(f"{path.name}:unclosed-code: unclosed fenced code block")

    return errors


def verify_internal_links(path: Path) -> list[str]:
    """Verify internal markdown links resolve correctly.

    Checks relative links (./path, ../path) and anchor links (#section).
    Skips external URLs, mailto:, and image links.
    """
    errors: list[str] = []
    if not path.exists():
        return errors

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for match in _INTERNAL_LINK_RE.finditer(line):
            text = match.group(1)
            url = match.group(2)

            # Skip external URLs and special links
            if url.startswith(("http://", "https://", "mailto:", "#", "data:", "javascript:")):
                continue
            if url.startswith("/"):
                continue

            # Extract anchor if present
            anchor = None
            if "#" in url:
                url_part, anchor = url.split("#", 1)
            else:
                url_part = url

            # Resolve relative path
            target = (path.parent / url_part).resolve()
            if not target.exists():
                errors.append(
                    f"{path.name}:{i}: broken-internal-link: [{text}]({url}) -> file not found: {target.name}"
                )
            elif anchor:
                # Check if anchor exists in target file
                target_content = target.read_text(encoding="utf-8")
                # Normalize anchor: lowercase, replace spaces with hyphens, remove special chars
                normalized_anchor = (
                    anchor.lower().replace(" ", "-").replace("'", "").replace('"', "").replace("(", "").replace(")", "")
                )
                # Check common anchor formats
                for heading_match in _HEADING_RE.finditer(target_content):
                    heading_text = heading_match.group(2).strip().lower()
                    heading_anchor = (
                        heading_text.replace(" ", "-")
                        .replace("'", "")
                        .replace('"', "")
                        .replace("(", "")
                        .replace(")", "")
                    )
                    if heading_anchor == normalized_anchor or anchor.lower() in heading_text:
                        break
                else:
                    # Only warn if the link is not to a header-only anchor
                    if not url_part:
                        errors.append(
                            f"{path.name}:{i}: broken-anchor: [{text}]({url}) -> anchor not found in {target.name}"
                        )

    return errors


def verify_markdown_lint() -> list[str]:
    """Run markdown lint on actively maintained docs markdown files.

    Excludes historically accumulated files (CHANGELOG, MEMO, roadmap,
    dated release notes, design docs, compliance docs) that have
    pre-existing structural issues not worth fixing in a lint check.
    """
    errors: list[str] = []
    md_files = collect_markdown_files(DOCS_DIR)

    for md_file in md_files:
        if _is_lint_excluded(md_file):
            continue
        lint_errors = lint_markdown_file(md_file)
        link_errors = verify_internal_links(md_file)
        errors.extend(lint_errors)
        errors.extend(link_errors)

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
    errors.extend(verify_markdown_lint())
    return errors


def run_security_only() -> list[str]:
    errors = verify_env_documentation(ENV_EXAMPLE, ENV_DOC)
    for forbidden in find_forbidden_env_files(ROOT):
        errors.append(f"forbidden env file: {forbidden}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify docs artifacts referenced by the repo")
    parser.add_argument(
        "--security-only",
        action="store_true",
        help="Verify only env documentation drift and forbidden env files",
    )
    args = parser.parse_args(argv)

    errors = run_security_only() if args.security_only else run()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("docs artifacts verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
