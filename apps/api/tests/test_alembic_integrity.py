from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_VERSIONS = REPO_ROOT / "alembic" / "versions"
ALEMBIC_ENV = REPO_ROOT / "alembic" / "env.py"


def _load_revision_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_alembic_versions_define_revision_metadata_and_import_cleanly():
    revision_files = sorted(ALEMBIC_VERSIONS.glob("*.py"))
    assert revision_files, "expected Alembic revision files"

    missing_metadata: list[str] = []

    for path in revision_files:
        module = _load_revision_module(path)
        if not hasattr(module, "revision") or not hasattr(module, "down_revision"):
            missing_metadata.append(path.name)

    assert not missing_metadata, (
        "Alembic revisions must import cleanly and define revision/down_revision: "
        + ", ".join(missing_metadata)
    )


def test_alembic_versions_do_not_use_exec_driver_sql():
    revision_files = sorted(ALEMBIC_VERSIONS.glob("*.py"))
    assert revision_files, "expected Alembic revision files"

    offenders = []
    for path in revision_files:
        contents = path.read_text(encoding="utf-8")
        if "op.exec_driver_sql(" in contents:
            offenders.append(path.name)

    assert not offenders, (
        "Alembic revisions must use op.execute(sa.text(...)) instead of op.exec_driver_sql(...): "
        + ", ".join(offenders)
    )


def test_alembic_env_version_table_width_covers_revision_ids():
    revision_files = sorted(ALEMBIC_VERSIONS.glob("*.py"))
    assert revision_files, "expected Alembic revision files"

    max_revision_len = 0
    for path in revision_files:
        module = _load_revision_module(path)
        if hasattr(module, "revision"):
            max_revision_len = max(max_revision_len, len(module.revision))

    env_text = ALEMBIC_ENV.read_text(encoding="utf-8")
    match = re.search(r"ALEMBIC_VERSION_NUM_LENGTH\s*=\s*(\d+)", env_text)
    assert match, "alembic/env.py must declare ALEMBIC_VERSION_NUM_LENGTH"

    assert int(match.group(1)) >= max_revision_len, (
        "alembic/env.py version table width must cover the longest revision id"
    )


def test_alembic_env_widens_existing_version_table_before_migration():
    env_text = ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "ALTER TABLE IF EXISTS alembic_version" in env_text
    assert "ALTER COLUMN version_num TYPE VARCHAR" in env_text


def test_query_audit_contract_columns_are_migrated_in_revision_0055():
    revision_path = (
        ALEMBIC_VERSIONS / "20260503_0055_query_audit_response_payload.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "ADD COLUMN IF NOT EXISTS tool_name",
        "ADD COLUMN IF NOT EXISTS sources",
        "ADD COLUMN IF NOT EXISTS confidence",
        "ADD COLUMN IF NOT EXISTS completeness",
        "ADD COLUMN IF NOT EXISTS verified",
        "ADD COLUMN IF NOT EXISTS response_payload",
    ):
        assert fragment in contents
