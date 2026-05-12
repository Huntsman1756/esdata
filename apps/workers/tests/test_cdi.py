"""Tests for CDI worker telemetry."""

import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cdi


def _engine_with_sync_log():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    rows_processed INTEGER,
                    errors INTEGER,
                    error_msg TEXT
                )
                """
            )
        )
    return engine


def test_write_sync_log_records_cron_worker_name(monkeypatch):
    engine = _engine_with_sync_log()
    monkeypatch.setattr(cdi, "WORKER_NAME", "cron-cdi-weekly")

    cdi._write_sync_log(
        engine,
        datetime.now(UTC),
        {
            "conventions_upserted": 86,
            "errors": 0,
            "with_firma": 82,
            "with_vigencia": 73,
            "with_pdfs": 84,
            "with_boe": 82,
        },
    )

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT worker, status, rows_processed, errors, error_msg
                FROM sync_log
                """
            )
        ).mappings().one()

    assert row["worker"] == "cron-cdi-weekly"
    assert row["status"] == "ok"
    assert row["rows_processed"] == 86
    assert row["errors"] == 0
    assert "conventions_upserted" in row["error_msg"]


def test_write_sync_log_marks_partial_when_some_rows_and_errors(monkeypatch):
    engine = _engine_with_sync_log()
    monkeypatch.setattr(cdi, "WORKER_NAME", "worker-cdi")

    cdi._write_sync_log(
        engine,
        datetime.now(UTC),
        {"conventions_upserted": 12, "errors": 1},
    )

    with engine.connect() as conn:
        row = conn.execute(text("SELECT worker, status, rows_processed, errors FROM sync_log")).mappings().one()

    assert dict(row) == {
        "worker": "worker-cdi",
        "status": "partial",
        "rows_processed": 12,
        "errors": 1,
    }
