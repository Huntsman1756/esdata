from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "maintenance" / "verify-doc-artifacts.py"
SPEC = importlib.util.spec_from_file_location("verify_doc_artifacts", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".tmp_verify_doc_artifacts"


def _reset_tmp_dir() -> Path:
    if TEST_TMP_ROOT.exists():
        shutil.rmtree(TEST_TMP_ROOT)
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return TEST_TMP_ROOT


def test_verify_artifact_accepts_valid_json():
    tmp_dir = _reset_tmp_dir()
    artifact = tmp_dir / "artifact.json"
    artifact.write_text('{"openapi": "3.1.0"}', encoding="utf-8")

    assert MODULE.verify_artifact(artifact) == []


def test_verify_artifact_reports_invalid_json():
    tmp_dir = _reset_tmp_dir()
    artifact = tmp_dir / "artifact.json"
    artifact.write_text('{"openapi": ', encoding="utf-8")

    errors = MODULE.verify_artifact(artifact)

    assert len(errors) == 1
    assert "invalid json" in errors[0]


def test_verify_reference_reports_missing_artifact():
    tmp_dir = _reset_tmp_dir()
    docs_file = tmp_dir / "README.md"
    docs_file.write_text("See openapi-gpt.json", encoding="utf-8")

    original_artifacts = MODULE.ARTIFACTS
    try:
        MODULE.ARTIFACTS = [tmp_dir / "openapi-gpt.json"]
        errors = MODULE.verify_reference(docs_file)
    finally:
        MODULE.ARTIFACTS = original_artifacts

    assert len(errors) == 1
    assert "doc references missing artifact" in errors[0]


def test_verify_reference_reports_broken_relative_link():
    tmp_dir = _reset_tmp_dir()
    docs_file = tmp_dir / "README.md"
    docs_file.write_text("See ../missing-file.md", encoding="utf-8")

    errors = MODULE.verify_reference(docs_file)

    assert len(errors) == 1
    assert "broken relative link" in errors[0]


def test_verify_artifact_detects_drift_against_expected_json():
    tmp_dir = _reset_tmp_dir()
    artifact = tmp_dir / "openapi-gpt.json"
    artifact.write_text('{"openapi": "3.1.0", "paths": {}}', encoding="utf-8")

    errors = MODULE.verify_artifact(
        artifact,
        expected_payload={"openapi": "3.1.0", "paths": {"/x": {}}},
    )

    assert len(errors) == 1
    assert "artifact drift" in errors[0]


def test_expected_payload_for_openapi_gpt_uses_active_desuscribir_domain():
    payload = MODULE.expected_payload_for_artifact(MODULE.DOCS_DIR / "openapi-gpt.json")

    assert payload is not None
    assert payload["servers"][0]["url"] == "https://api.desuscribir.es"


def test_expected_payload_for_openapi_gpt_30_uses_active_desuscribir_domain():
    payload = MODULE.expected_payload_for_artifact(MODULE.DOCS_DIR / "openapi-gpt-3.0.json")

    assert payload is not None
    assert payload["servers"][0]["url"] == "https://api.desuscribir.es"


def test_main_returns_non_zero_when_drift_detected():
    tmp_dir = _reset_tmp_dir()
    artifact = tmp_dir / "openapi-gpt.json"
    artifact.write_text('{"openapi": "3.1.0", "paths": {}}', encoding="utf-8")

    original_artifacts = MODULE.ARTIFACTS
    original_expected = MODULE.expected_payload_for_artifact
    original_docs_refs = MODULE.DOCS_REFERENCES
    original_env_example = MODULE.ENV_EXAMPLE
    original_env_doc = MODULE.ENV_DOC
    original_find_forbidden = MODULE.find_forbidden_env_files
    original_verify_docs_vs_roadmap = MODULE.verify_docs_vs_roadmap
    original_verify_workers_documented = MODULE.verify_workers_documented
    original_verify_endpoints_documented = MODULE.verify_endpoints_documented
    original_verify_markdown_lint = MODULE.verify_markdown_lint
    try:
        MODULE.ARTIFACTS = [artifact]
        MODULE.DOCS_REFERENCES = []
        MODULE.ENV_EXAMPLE = tmp_dir / ".env.example"
        MODULE.ENV_EXAMPLE.write_text("ESDATA_API_KEY=test\n", encoding="utf-8")
        MODULE.ENV_DOC = tmp_dir / "environment-variables.md"
        MODULE.ENV_DOC.write_text("| Variable |\n|---|\n| `ESDATA_API_KEY` |\n", encoding="utf-8")
        MODULE.expected_payload_for_artifact = lambda _path: {"openapi": "3.1.0", "paths": {"/x": {}}}
        MODULE.find_forbidden_env_files = lambda _root: []
        MODULE.verify_docs_vs_roadmap = lambda: []
        MODULE.verify_workers_documented = lambda: []
        MODULE.verify_endpoints_documented = lambda: []
        MODULE.verify_markdown_lint = lambda: []
        errors = MODULE.run()
    finally:
        MODULE.ARTIFACTS = original_artifacts
        MODULE.expected_payload_for_artifact = original_expected
        MODULE.DOCS_REFERENCES = original_docs_refs
        MODULE.ENV_EXAMPLE = original_env_example
        MODULE.ENV_DOC = original_env_doc
        MODULE.find_forbidden_env_files = original_find_forbidden
        MODULE.verify_docs_vs_roadmap = original_verify_docs_vs_roadmap
        MODULE.verify_workers_documented = original_verify_workers_documented
        MODULE.verify_endpoints_documented = original_verify_endpoints_documented
        MODULE.verify_markdown_lint = original_verify_markdown_lint

    assert len(errors) == 1
    assert "artifact drift" in errors[0]


def test_ci_baseline_skips_artifact_drift_until_docs_baseline_is_adopted():
    tmp_dir = _reset_tmp_dir()
    artifact = tmp_dir / "openapi-gpt.json"
    artifact.write_text('{"openapi": "3.1.0", "paths": {}}', encoding="utf-8")

    original_artifacts = MODULE.ARTIFACTS
    original_docs_refs = MODULE.DOCS_REFERENCES
    original_env_example = MODULE.ENV_EXAMPLE
    original_env_doc = MODULE.ENV_DOC
    original_find_forbidden = MODULE.find_forbidden_env_files
    try:
        MODULE.ARTIFACTS = [artifact]
        MODULE.DOCS_REFERENCES = []
        MODULE.ENV_EXAMPLE = tmp_dir / ".env.example"
        MODULE.ENV_EXAMPLE.write_text("ESDATA_API_KEY=test\n", encoding="utf-8")
        MODULE.ENV_DOC = tmp_dir / "environment-variables.md"
        MODULE.ENV_DOC.write_text("| Variable |\n|---|\n| `ESDATA_API_KEY` |\n", encoding="utf-8")
        MODULE.find_forbidden_env_files = lambda _root: []

        errors = MODULE.run_ci_baseline()
    finally:
        MODULE.ARTIFACTS = original_artifacts
        MODULE.DOCS_REFERENCES = original_docs_refs
        MODULE.ENV_EXAMPLE = original_env_example
        MODULE.ENV_DOC = original_env_doc
        MODULE.find_forbidden_env_files = original_find_forbidden

    assert errors == []


def test_extract_env_example_variables_reads_assignments():
    tmp_dir = _reset_tmp_dir()
    env_file = tmp_dir / ".env.example"
    env_file.write_text(
        "# comment\nESDATA_API_KEY=test\nMCP_API_KEY=other\nINVALID LINE\n",
        encoding="utf-8",
    )

    variables = MODULE.extract_env_example_variables(env_file)

    assert variables == {"ESDATA_API_KEY", "MCP_API_KEY"}


def test_extract_documented_variables_reads_backticked_names():
    tmp_dir = _reset_tmp_dir()
    docs_file = tmp_dir / "environment-variables.md"
    docs_file.write_text(
        "| Variable |\n|---|\n| `ESDATA_API_KEY` |\n| `MCP_API_KEY` |\n",
        encoding="utf-8",
    )

    variables = MODULE.extract_documented_variables(docs_file)

    assert variables == {"ESDATA_API_KEY", "MCP_API_KEY"}


def test_verify_env_documentation_reports_missing_and_extra_variables():
    tmp_dir = _reset_tmp_dir()
    env_file = tmp_dir / ".env.example"
    env_file.write_text("ESDATA_API_KEY=test\nONLY_IN_ENV=1\n", encoding="utf-8")
    docs_file = tmp_dir / "environment-variables.md"
    docs_file.write_text(
        "| Variable |\n|---|\n| `ESDATA_API_KEY` |\n| `ONLY_IN_DOCS` |\n",
        encoding="utf-8",
    )

    errors = MODULE.verify_env_documentation(env_file, docs_file)

    assert len(errors) == 2
    assert "missing in docs/environment-variables.md: ONLY_IN_ENV" in errors[0]
    assert "missing in .env.example: ONLY_IN_DOCS" in errors[1]


def test_find_forbidden_env_files_flags_nested_and_root_runtime_env_files():
    tmp_dir = _reset_tmp_dir()
    allowed = tmp_dir / ".env.example"
    allowed.write_text("ESDATA_API_KEY=test\n", encoding="utf-8")
    forbidden_root = tmp_dir / ".env"
    forbidden_root.write_text("SECRET=x\n", encoding="utf-8")
    nested_dir = tmp_dir / "apps" / "api"
    nested_dir.mkdir(parents=True, exist_ok=True)
    forbidden_nested = nested_dir / ".env"
    forbidden_nested.write_text("SECRET=y\n", encoding="utf-8")

    findings = MODULE.find_forbidden_env_files(tmp_dir)

    assert findings == [
        ".env",
        "apps/api/.env",
    ]
