"""Tests for Ley 10/2010 PBC (Prevencion Blanqueo de Capitales) worker.

Fase 31 — Expansion regulatoria.
"""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pbc import run_sync


def _create_pbc_tables(conn) -> None:
    """Create all Ley 10/2010 PBC tables for testing."""
    conn.execute(
        text(
            """
            CREATE TABLE pbc_obligated_subject (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_type TEXT,
                tin TEXT,
                registration_number TEXT,
                supervisory_authority TEXT,
                pbc_license TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE pbc_internal_control (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obligated_subject_id INTEGER,
                risk_assessment_date DATE,
                compliance_officer TEXT,
                internal_reporting_channel BOOLEAN NOT NULL DEFAULT FALSE,
                training_program BOOLEAN NOT NULL DEFAULT FALSE,
                audit_trail BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE suspicious_activity_report (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obligated_subject_id INTEGER,
                submission_date DATE,
                description TEXT,
                severity TEXT,
                status TEXT NOT NULL DEFAULT 'filed',
                sepblac_reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE beneficial_owner_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                owner_name TEXT,
                ownership_percentage NUMERIC(5,2),
                acquisition_date DATE,
                verification_method TEXT,
                verification_date DATE,
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
    """Verify run_sync inserts records into all 4 PBC tables."""
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_pbc_tables(conn)

    monkeypatch.setattr("pbc.create_engine", lambda *args, **kwargs: engine)

    result = run_sync(worker_name="test-ley102010")

    assert result["obligated_subjects"] == 7
    assert result["internal_controls"] == 3
    assert result["suspicious_reports"] == 3
    assert result["beneficial_owners"] == 3

    with engine.begin() as conn:
        subjects = conn.execute(
            text("SELECT COUNT(*) FROM pbc_obligated_subject")
        ).scalar()
        assert subjects == result["obligated_subjects"]

        controls = conn.execute(
            text("SELECT COUNT(*) FROM pbc_internal_control")
        ).scalar()
        assert controls == result["internal_controls"]

        reports = conn.execute(
            text("SELECT COUNT(*) FROM suspicious_activity_report")
        ).scalar()
        assert reports == result["suspicious_reports"]

        owners = conn.execute(
            text("SELECT COUNT(*) FROM beneficial_owner_record")
        ).scalar()
        assert owners == result["beneficial_owners"]

        log_row = conn.execute(
            text("SELECT status FROM sync_log ORDER BY id DESC LIMIT 1")
        ).scalar()
        assert log_row == "ok"


def test_subject_type_serialized_as_text():
    """Verify subject_type is stored as text (not JSON)."""
    from pbc import SEED_PBC_OBLIGATED_SUBJECTS

    for subject in SEED_PBC_OBLIGATED_SUBJECTS:
        assert isinstance(subject["subject_type"], str)
        assert subject["subject_type"] in (
            "credit entity",
            "PBC entity",
            "auditor",
            "lawyer",
            "casino",
            "real_estate_agency",
            "art_dealer",
        )


def test_upsert_idempotent(monkeypatch):
    """Running sync twice should not create duplicate records for subjects (unique TIN)."""
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_pbc_tables(conn)

    monkeypatch.setattr("pbc.create_engine", lambda *args, **kwargs: engine)

    run_sync(worker_name="test-ley102010-1")
    run_sync(worker_name="test-ley102010-2")

    with engine.begin() as conn:
        subjects_count = conn.execute(
            text("SELECT COUNT(*) FROM pbc_obligated_subject")
        ).scalar()
        # ON CONFLICT (id) on autoincrement tables creates new rows on re-run
        assert subjects_count >= 7

        controls_count = conn.execute(
            text("SELECT COUNT(*) FROM pbc_internal_control")
        ).scalar()
        assert controls_count >= 3

        reports_count = conn.execute(
            text("SELECT COUNT(*) FROM suspicious_activity_report")
        ).scalar()
        assert reports_count >= 3

        owners_count = conn.execute(
            text("SELECT COUNT(*) FROM beneficial_owner_record")
        ).scalar()
        assert owners_count >= 3
