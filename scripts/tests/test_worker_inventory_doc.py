from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RETRY_DOC = ROOT / "docs" / "worker-db-retry-coverage.md"
INVENTORY_DOC = ROOT / "docs" / "worker-inventory.md"

VALID_TYPES = {
    "active-persistent",
    "active-cron",
    "helper/module",
    "dead/unused",
}


def _retry_worker_files() -> list[str]:
    text = RETRY_DOC.read_text(encoding="utf-8")
    return re.findall(r"\| `([^`]+\.py)` \| \d+ \| PASS \|", text)


def _inventory_rows() -> dict[str, str]:
    text = INVENTORY_DOC.read_text(encoding="utf-8")
    rows: dict[str, str] = {}
    for match in re.finditer(
        r"^\| `(?P<file>[^`]+\.py)` \| `(?P<type>[^`]+)` \|",
        text,
        re.MULTILINE,
    ):
        file = match.group("file")
        worker_type = match.group("type")
        assert file not in rows, f"duplicate inventory row for {file}"
        rows[file] = worker_type
    return rows


def test_worker_inventory_covers_all_retry_guarded_db_workers_once() -> None:
    retry_workers = sorted(_retry_worker_files())
    inventory_rows = _inventory_rows()

    assert len(retry_workers) == 68
    assert sorted(inventory_rows) == retry_workers


def test_worker_inventory_uses_only_a12_classification_types() -> None:
    rows = _inventory_rows()

    assert rows
    assert set(rows.values()) <= VALID_TYPES
    assert set(rows.values()) == VALID_TYPES


def test_worker_inventory_has_no_ambiguous_placeholders() -> None:
    text = INVENTORY_DOC.read_text(encoding="utf-8").lower()

    assert "todo" not in text
    assert "tbd" not in text
    assert "ambiguous" not in text
