from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKERS_DIR = ROOT / "apps" / "workers"


def _worker_files() -> list[Path]:
    return sorted(
        path
        for path in WORKERS_DIR.glob("*.py")
        if path.name != "runtime.py" and not path.name.startswith("test_")
    )


def test_every_worker_that_creates_db_engine_checks_connection_first():
    missing = []
    for path in _worker_files():
        text = path.read_text(encoding="utf-8")
        if "create_engine(" not in text:
            continue
        if "ensure_database_connection" not in text:
            missing.append(path.name)

    assert missing == []


def test_runtime_import_branches_that_use_database_url_import_retry_guard():
    missing = []
    for path in _worker_files():
        text = path.read_text(encoding="utf-8")
        if "create_engine(" not in text:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if "from runtime import" not in stripped and "from .runtime import" not in stripped:
                continue
            if "get_database_url" in stripped and "ensure_database_connection" not in stripped:
                missing.append(f"{path.name}: {stripped}")

    assert missing == []


def test_worker_db_retry_coverage_doc_matches_current_inventory():
    doc = (ROOT / "docs" / "worker-db-retry-coverage.md").read_text(encoding="utf-8")
    in_scope = []
    for path in _worker_files():
        text = path.read_text(encoding="utf-8")
        if "create_engine(" in text:
            in_scope.append(path.name)

    assert f"In-scope DB worker files: {len(in_scope)}" in doc
    assert "Missing retry guard: 0" in doc
    for name in in_scope:
        assert f"`{name}`" in doc
