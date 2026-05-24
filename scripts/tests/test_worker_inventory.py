from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKERS_DIR = ROOT / "apps" / "workers"
COMPOSE_FILE = ROOT / "infra" / "deploy" / "docker-compose.prod.yml"
INVENTORY_FILE = ROOT / "docs" / "worker-inventory.md"
RETRY_DOC = ROOT / "docs" / "worker-db-retry-coverage.md"

EXPECTED_A12_COUNTS = {
    "active-persistent": 14,
    "active-cron": 14,
    "helper/module": 31,
    "dead/unused": 9,
}

COMPOSE_WRAPPER_TO_DB_WORKER = {
    "worker_eurlex_market.py": "eurlex_market.py",
}


def _retry_worker_files() -> set[str]:
    text = RETRY_DOC.read_text(encoding="utf-8")
    return set(re.findall(r"\| `([^`]+\.py)` \| \d+ \| PASS \|", text))


def _out_of_scope_worker_files() -> set[str]:
    text = RETRY_DOC.read_text(encoding="utf-8")
    match = re.search(
        r"Out-of-scope helper/dataset(?:/wrapper)? modules without `create_engine\(\.\.\.\)`: (?P<files>.+)\.",
        text,
    )
    assert match, "worker retry doc must list out-of-scope helper modules"
    return set(re.findall(r"`([^`]+\.py)`", match.group("files")))


def _inventory_rows() -> dict[str, dict[str, str]]:
    text = INVENTORY_FILE.read_text(encoding="utf-8")
    rows: dict[str, dict[str, str]] = {}
    for match in re.finditer(
        r"^\| `(?P<file>[^`]+\.py)` \| `(?P<type>[^`]+)` \| "
        r"(?P<services>[^|]+) \| (?P<status_worker>[^|]+) \| "
        r"(?P<timer>[^|]+) \| (?P<comment>[^|]+) \|$",
        text,
        re.MULTILINE,
    ):
        file_name = match.group("file")
        assert file_name not in rows, f"duplicate inventory row for {file_name}"
        rows[file_name] = {
            "type": match.group("type"),
            "services": match.group("services").strip(),
            "status_worker": match.group("status_worker").strip(),
            "timer": match.group("timer").strip(),
            "comment": match.group("comment").strip(),
        }
    return rows


def _compose_worker_files() -> dict[str, set[str]]:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    result: dict[str, set[str]] = {}
    for match in re.finditer(
        r"^  (?P<service>[A-Za-z0-9_-]+):\n(?P<body>(?:    .*(?:\n|$))*)",
        text,
        re.MULTILINE,
    ):
        command = re.search(r"WORKER_CMD:\s*python\s+([A-Za-z0-9_]+\.py)", match.group("body"))
        if not command:
            continue
        db_worker_file = COMPOSE_WRAPPER_TO_DB_WORKER.get(command.group(1), command.group(1))
        result.setdefault(db_worker_file, set()).add(match.group("service"))
    return result


def test_worker_inventory_classifies_only_retry_guarded_db_workers() -> None:
    inventory_rows = _inventory_rows()

    assert len(inventory_rows) == 68
    assert set(inventory_rows) == _retry_worker_files()


def test_worker_inventory_a12_type_counts_are_explicit() -> None:
    counts = Counter(row["type"] for row in _inventory_rows().values())

    assert counts == EXPECTED_A12_COUNTS


def test_worker_inventory_keeps_out_of_scope_helpers_out_of_a12_rows() -> None:
    worker_files = {path.name for path in WORKERS_DIR.glob("*.py")}
    classified_or_excluded = _retry_worker_files() | _out_of_scope_worker_files()

    assert worker_files == classified_or_excluded
    assert _out_of_scope_worker_files().isdisjoint(_inventory_rows())


def test_compose_worker_commands_are_documented_in_active_inventory_rows() -> None:
    inventory_rows = _inventory_rows()
    compose_workers = _compose_worker_files()

    assert len(compose_workers) == 28
    for worker_file, services in compose_workers.items():
        assert worker_file in inventory_rows
        assert inventory_rows[worker_file]["type"] in {"active-persistent", "active-cron"}
        documented_services = set(re.findall(r"`([^`]+)`", inventory_rows[worker_file]["services"]))
        assert services <= documented_services


def test_helper_modules_are_visible_manual_or_backlog_debt() -> None:
    helper_rows = {
        file_name: row
        for file_name, row in _inventory_rows().items()
        if row["type"] == "helper/module"
    }

    assert len(helper_rows) == 31
    for file_name, row in helper_rows.items():
        assert row["services"] == "none", file_name
        assert row["status_worker"] == "none current", file_name
        assert row["timer"] == "no", file_name
        assert row["comment"], file_name
