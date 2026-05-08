from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "maintenance" / "secrets_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("secrets_audit", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tmp_file(tmp_path: Path, name: str, content: str) -> Path:
    target = tmp_path / name
    target.write_text(content, encoding="utf-8")
    return target


def test_scan_file_reports_real_database_password(tmp_path: Path):
    module = _load_module()
    target = _tmp_file(
        tmp_path,
        "script.py",
        'DATABASE_URL = "postgresql://prod_user:real-secret-123@example.com:5432/app"\n',
    )

    findings = module.scan_file(target)

    assert len(findings) == 1
    assert findings[0].pattern == "DB Connection String"
    assert findings[0].severity == "high"


def test_scan_file_ignores_local_placeholder_database_url(tmp_path: Path):
    module = _load_module()
    target = _tmp_file(
        tmp_path,
        "seed.py",
        'DATABASE_URL = "postgresql://esdata:esdata_dev@localhost:5432/esdata"\n',
    )

    findings = module.scan_file(target)

    assert findings == []


def test_should_skip_historical_agent_docs():
    module = _load_module()

    assert module.should_skip(Path("docs/superpowers/plans/example.md"))
    assert module.should_skip(Path("docs/archive/postmortems/example.md"))
    assert module.should_skip(Path(".agents/skills/example/SKILL.md"))
