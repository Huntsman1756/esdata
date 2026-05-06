from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "maintenance" / "secrets_audit.py"
SPEC = importlib.util.spec_from_file_location("secrets_audit", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_local_development_database_url_is_not_reported(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample = tmp_path / "seed.py"
    sample.write_text(
        'DB_URL = "postgresql://esdata:esdata_dev@localhost:5432/esdata"\n',
        encoding="utf-8",
    )

    findings = MODULE.scan_file(sample)

    assert not findings


def test_placeholder_database_url_is_not_reported(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample = tmp_path / "example.py"
    sample.write_text(
        'example = "postgresql://user:pass@host:5432/db"\n',
        encoding="utf-8",
    )

    findings = MODULE.scan_file(sample)

    assert not findings


def test_external_database_url_with_password_is_reported(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample = tmp_path / "unsafe.py"
    sample.write_text(
        'DB_URL = "postgresql://admin:secret123@db.internal:5432/app"\n',
        encoding="utf-8",
    )

    findings = MODULE.scan_file(sample)

    assert len(findings) == 1
    assert findings[0].pattern == "DB Connection String"


def test_scan_directory_skips_tests_on_platform_native_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tests_dir = tmp_path / "scripts" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_example.py").write_text(
        'DB_URL = "postgresql://admin:secret123@db.internal:5432/app"\n',
        encoding="utf-8",
    )

    findings = MODULE.scan_directory(tmp_path)

    assert not findings


def test_placeholder_password_hash_is_not_reported(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample = tmp_path / "runbook.md"
    sample.write_text(
        "\"UPDATE user SET password = '$2a$10$...', salt = '' WHERE login = 'admin';\"\n",
        encoding="utf-8",
    )

    findings = MODULE.scan_file(sample)

    assert not findings
