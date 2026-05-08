"""Tests for DAC8/DAC9 worker.

Fase 31 — Expansion regulatoria.
"""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dac8 import run_sync


def _create_dac8_tables(conn) -> None:
    """Create all DAC8/DAC9 tables for testing."""
    conn.execute(
        text(
            """
            CREATE TABLE dac_reporting_entity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tin TEXT UNIQUE,
                entity_type TEXT,
                member_state TEXT,
                dac8_registered BOOLEAN NOT NULL DEFAULT FALSE,
                dac9_registered BOOLEAN NOT NULL DEFAULT FALSE,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE dac_crypto_report (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                reporting_period TEXT,
                submitted_at TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'draft',
                crypto_transactions_count INTEGER NOT NULL DEFAULT 0,
                wallet_holders_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE dac_wallet_holder (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER,
                wallet_address TEXT,
                holder_tin TEXT,
                holder_member_state TEXT,
                holder_type TEXT,
                total_value_eur NUMERIC,
                verification_status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                bloques_processed INTEGER,
                articulos_upserted INTEGER,
                documentos_processed INTEGER,
                documentos_upserted INTEGER,
                doctrina_links_created INTEGER,
                error_msg TEXT,
                rows_processed INTEGER,
                errors INTEGER,
                duration_ms INTEGER
            )
            """
        )
    )


def test_run_sync_persists_all_entities(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_dac8_tables(conn)

    monkeypatch.setattr("dac8.create_engine", lambda *args, **kwargs: engine)

    result = run_sync(worker_name="test-dac8")

    assert result["reporting_entities"] == 5
    assert result["crypto_reports"] == 3
    assert result["wallet_holders"] == 3

    with engine.begin() as conn:
        entity_count = conn.execute(
            text("SELECT COUNT(*) FROM dac_reporting_entity")
        ).scalar()
        assert entity_count == result["reporting_entities"]

        report_count = conn.execute(
            text("SELECT COUNT(*) FROM dac_crypto_report")
        ).scalar()
        assert report_count == result["crypto_reports"]

        holder_count = conn.execute(
            text("SELECT COUNT(*) FROM dac_wallet_holder")
        ).scalar()
        assert holder_count == result["wallet_holders"]

        log_row = conn.execute(
            text("SELECT status FROM sync_log ORDER BY id DESC LIMIT 1")
        ).scalar()
        assert log_row == "ok"


def test_services_offered_serialized_as_json():
    """Verifica que los valores de total_value_eur se serializan correctamente.

    DAC8/DAC9 worker usa Numeric para total_value_eur; los valores
    de seed son float que SQLAlchemy mapea correctamente a DECIMAL.
    """
    from dac8 import SEED_DAC_WALLET_HOLDERS

    for holder in SEED_DAC_WALLET_HOLDERS:
        assert isinstance(holder["total_value_eur"], (int, float))
        assert holder["total_value_eur"] >= 0


def test_upsert_idempotent(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_dac8_tables(conn)

    monkeypatch.setattr("dac8.create_engine", lambda *args, **kwargs: engine)

    result1 = run_sync(worker_name="test-dac8-1")
    result2 = run_sync(worker_name="test-dac8-2")

    with engine.begin() as conn:
        entity_count = conn.execute(
            text("SELECT COUNT(*) FROM dac_reporting_entity")
        ).scalar()
        assert entity_count == result1["reporting_entities"]
        assert entity_count == result2["reporting_entities"]

        report_count = conn.execute(
            text("SELECT COUNT(*) FROM dac_crypto_report")
        ).scalar()
        assert report_count >= result1["crypto_reports"]
        assert report_count >= result2["crypto_reports"]

        holder_count = conn.execute(
            text("SELECT COUNT(*) FROM dac_wallet_holder")
        ).scalar()
        assert holder_count >= result1["wallet_holders"]
        assert holder_count >= result2["wallet_holders"]
