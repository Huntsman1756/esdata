import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mica import run_sync


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


def test_run_sync_persists_all_entities(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)

    result = run_sync(worker_name="test-mica")

    assert result["casps"] > 0
    assert result["crypto_assets"] > 0
    assert result["tokenized_assets"] > 0
    assert result["wallet_custodians"] > 0
    assert result["crypto_transactions"] > 0

    with engine.begin() as conn:
        casp_count = conn.execute(text("SELECT COUNT(*) FROM casp")).scalar()
        assert casp_count == result["casps"]

        asset_count = conn.execute(text("SELECT COUNT(*) FROM crypto_asset")).scalar()
        assert asset_count == result["crypto_assets"]

        tokenized_count = conn.execute(
            text("SELECT COUNT(*) FROM tokenized_asset")
        ).scalar()
        assert tokenized_count == result["tokenized_assets"]

        custodian_count = conn.execute(
            text("SELECT COUNT(*) FROM wallet_custodian")
        ).scalar()
        assert custodian_count == result["wallet_custodians"]

        tx_count = conn.execute(
            text("SELECT COUNT(*) FROM crypto_transaction")
        ).scalar()
        assert tx_count == result["crypto_transactions"]

        log_row = conn.execute(
            text("SELECT status FROM sync_log ORDER BY id DESC LIMIT 1")
        ).scalar()
        assert log_row == "ok"


def test_services_offered_serialized_as_json(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)

    run_sync(worker_name="test-mica-services")

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT services_offered FROM casp WHERE name = 'Bitso'")
        ).scalar()
        assert row is not None
        parsed = json.loads(row)
        assert isinstance(parsed, dict)
        assert parsed["exchange"] is True
        assert parsed["custody"] is True


def test_upsert_idempotent(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)

    result1 = run_sync(worker_name="test-mica-1")
    result2 = run_sync(worker_name="test-mica-2")

    with engine.begin() as conn:
        casp_count = conn.execute(text("SELECT COUNT(*) FROM casp")).scalar()
        assert casp_count == result1["casps"]
        assert casp_count == result2["casps"]

        asset_count = conn.execute(
            text("SELECT COUNT(*) FROM crypto_asset")
        ).scalar()
        assert asset_count == result1["crypto_assets"]
        assert asset_count == result2["crypto_assets"]

        tx_count = conn.execute(
            text("SELECT COUNT(*) FROM crypto_transaction")
        ).scalar()
        assert tx_count == result1["crypto_transactions"]
        assert tx_count == result2["crypto_transactions"]
