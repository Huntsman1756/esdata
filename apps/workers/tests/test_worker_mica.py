import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mica import run_once


def _create_mica_tables(conn) -> None:
    """Create all MiCA tables for testing."""
    conn.execute(
        text(
            """
            CREATE TABLE casp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                registration_number TEXT UNIQUE,
                home_member_state TEXT,
                passport_active BOOLEAN NOT NULL DEFAULT FALSE,
                services_offered TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE crypto_asset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_type TEXT NOT NULL,
                reference_uid TEXT UNIQUE,
                issuer_jurisdiction TEXT,
                is_sha BOOLEAN NOT NULL DEFAULT FALSE,
                market_value_eur NUMERIC,
                holders_count INTEGER,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE tokenized_asset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                underlying_type TEXT,
                face_value NUMERIC,
                total_amount NUMERIC,
                listing_date DATE,
                regulated_market TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE wallet_custodian (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER UNIQUE,
                wallet_type TEXT,
                custody_mechanism TEXT,
                insurance_coverage NUMERIC,
                audit_frequency TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE crypto_transaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_wallet TEXT,
                receiver_wallet TEXT,
                sender_jurisdiction TEXT,
                receiver_jurisdiction TEXT,
                asset_type TEXT,
                amount NUMERIC,
                value_eur NUMERIC,
                timestamp TIMESTAMP,
                reporting_period TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sender_wallet, receiver_wallet, timestamp, reporting_period)
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


def test_run_once_persists_casp_entities(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "mica.fetch_esma_casp",
        lambda: [
            {
                "name": "Bitso",
                "registration_number": "ESMA-BITSO-001",
                "home_member_state": "ES",
                "passport_active": True,
                "custody": True,
                "exchange": True,
            }
        ],
    )

    run_once()

    with engine.begin() as conn:
        casp_count = conn.execute(text("SELECT COUNT(*) FROM casp")).scalar()
        assert casp_count == 1
        asset_count = conn.execute(text("SELECT COUNT(*) FROM crypto_asset")).scalar()
        assert asset_count == 0
        tokenized_count = conn.execute(text("SELECT COUNT(*) FROM tokenized_asset")).scalar()
        assert tokenized_count == 0
        custodian_count = conn.execute(text("SELECT COUNT(*) FROM wallet_custodian")).scalar()
        assert custodian_count == 0
        tx_count = conn.execute(text("SELECT COUNT(*) FROM crypto_transaction")).scalar()
        assert tx_count == 0


def test_services_offered_serialized_as_json(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "mica.fetch_esma_casp",
        lambda: [
            {
                "name": "Bitso",
                "registration_number": "ESMA-BITSO-001",
                "home_member_state": "ES",
                "passport_active": True,
                "custody": True,
                "exchange": True,
            }
        ],
    )

    run_once()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT services_offered FROM casp WHERE name = 'Bitso'")
        ).scalar()
        assert row is not None
        if isinstance(row, str):
            parsed = json.loads(row)
        else:
            parsed = row
        assert isinstance(parsed, list)
        assert "exchange" in parsed
        assert "custody" in parsed


def test_upsert_idempotent(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "mica.fetch_esma_casp",
        lambda: [
            {
                "name": "Bitso",
                "registration_number": "ESMA-BITSO-001",
                "home_member_state": "ES",
                "passport_active": True,
                "custody": True,
                "exchange": True,
            }
        ],
    )

    run_once()
    run_once()

    with engine.begin() as conn:
        casp_count = conn.execute(text("SELECT COUNT(*) FROM casp")).scalar()
        assert casp_count == 1
        asset_count = conn.execute(text("SELECT COUNT(*) FROM crypto_asset")).scalar()
        assert asset_count == 0
        tx_count = conn.execute(text("SELECT COUNT(*) FROM crypto_transaction")).scalar()
        assert tx_count == 0
