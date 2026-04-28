"""Tests for Ley 11/2021 (Prevencion de Fraude) worker.

Fase 31 — Expansion regulatoria.
"""

from pathlib import Path

from sqlalchemy import create_engine, text

sys_path = __import__("sys").path
sys_path.insert(0, str(Path(__file__).resolve().parents[1]))

from fraud import run_sync


def _create_fraud_tables(conn) -> None:
    """Create all Ley 11/2021 fraud tables for testing."""
    conn.execute(
        text(
            """
            CREATE TABLE fraud_prevention_program (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                code_of_conduct BOOLEAN NOT NULL DEFAULT FALSE,
                internal_reporting_system BOOLEAN NOT NULL DEFAULT FALSE,
                training_schedule TEXT,
                audit_frequency TEXT,
                compliance_officer_name TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE fraud_risk_assessment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                assessment_date DATE,
                risk_areas TEXT,
                mitigation_measures TEXT,
                next_review_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE fraud_incident (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                incident_date DATE,
                description TEXT,
                amount_eur NUMERIC(12,2),
                status TEXT NOT NULL DEFAULT 'open',
                resolution_date DATE,
                regulatory_notification BOOLEAN NOT NULL DEFAULT FALSE,
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
    """Verify run_sync inserts records into all 3 fraud tables."""
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_fraud_tables(conn)

    monkeypatch.setattr("fraud.create_engine", lambda *args, **kwargs: engine)

    result = run_sync(worker_name="test-ley112021")

    assert result["programs"] == 3
    assert result["assessments"] == 2
    assert result["incidents"] == 3

    with engine.begin() as conn:
        programs = conn.execute(
            text("SELECT COUNT(*) FROM fraud_prevention_program")
        ).scalar()
        assert programs == result["programs"]

        assessments = conn.execute(
            text("SELECT COUNT(*) FROM fraud_risk_assessment")
        ).scalar()
        assert assessments == result["assessments"]

        incidents = conn.execute(
            text("SELECT COUNT(*) FROM fraud_incident")
        ).scalar()
        assert incidents == result["incidents"]

        log_row = conn.execute(
            text("SELECT status FROM sync_log ORDER BY id DESC LIMIT 1")
        ).scalar()
        assert log_row == "ok"


def test_risk_areas_serialized_as_text():
    """Verify risk_areas JSON is stored as text string."""
    from fraud import SEED_FRAUD_RISK_ASSESSMENTS

    for assessment in SEED_FRAUD_RISK_ASSESSMENTS:
        assert isinstance(assessment["risk_areas"], str)


def test_upsert_idempotent(monkeypatch):
    """Running sync twice should not prevent duplicate rows on autoincrement tables."""
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_fraud_tables(conn)

    monkeypatch.setattr("fraud.create_engine", lambda *args, **kwargs: engine)

    run_sync(worker_name="test-ley112021-1")
    run_sync(worker_name="test-ley112021-2")

    with engine.begin() as conn:
        programs_count = conn.execute(
            text("SELECT COUNT(*) FROM fraud_prevention_program")
        ).scalar()
        assert programs_count >= 3

        assessments_count = conn.execute(
            text("SELECT COUNT(*) FROM fraud_risk_assessment")
        ).scalar()
        assert assessments_count >= 2

        incidents_count = conn.execute(
            text("SELECT COUNT(*) FROM fraud_incident")
        ).scalar()
        assert incidents_count >= 3
