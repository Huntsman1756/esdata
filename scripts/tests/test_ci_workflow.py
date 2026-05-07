from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _job_block(workflow: str, job_name: str) -> str:
    marker = f"  {job_name}:"
    _, remainder = workflow.split(marker, 1)
    lines: list[str] = []
    for line in remainder.splitlines():
        if line.startswith("  ") and not line.startswith("    "):
            break
        lines.append(line)
    return "\n".join(lines)


def test_database_backed_ci_jobs_use_pgvector_postgres_image():
    workflow = _read_workflow()

    for job_name in ("test-python", "test-integration", "eval-gate"):
        block = _job_block(workflow, job_name)

        assert "image: pgvector/pgvector:pg16@sha256:" in block
        assert "image: postgres:16-alpine" not in block


def test_security_audit_uses_security_only_doc_artifact_check():
    workflow = _read_workflow()
    block = _job_block(workflow, "security-audit")

    assert "verify-doc-artifacts.py --security-only" in block


def test_docs_artifacts_job_uses_artifact_only_doc_artifact_check():
    workflow = _read_workflow()
    block = _job_block(workflow, "docs-artifacts")

    assert "verify-doc-artifacts.py --artifacts-only" in block
