from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dead_letter import add_dead_letter, get_dead_letters, resolve_dead_letter


def _engine_with_dead_letter_table():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE sync_dead_letter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_name TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    error_message TEXT,
                    error_traceback TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    resolved BOOLEAN NOT NULL DEFAULT FALSE,
                    first_failed_at TEXT,
                    last_failed_at TEXT,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    notes TEXT
                )
                """
            )
        )
    return engine


def test_dead_letter_runtime_uses_boolean_filters_for_postgres_compatibility():
    engine = _engine_with_dead_letter_table()

    assert add_dead_letter(engine, "worker-dgt", "session_init", "session_init", "502") == 1
    assert len(get_dead_letters(engine)) == 1

    assert resolve_dead_letter(engine, 1, "pytest", "transient upstream recovered") is True
    assert get_dead_letters(engine) == []
    resolved = get_dead_letters(engine, resolved=True)
    assert len(resolved) == 1
    assert resolved[0]["worker_name"] == "worker-dgt"
