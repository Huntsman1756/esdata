"""Worker para ingestion de datos Ley 10/2010 PBC (Prevencion Blanqueo de Capitales).

Fase 31 — Expansion regulatoria.

Ingesta datos de:
- Sujetos obligados PBC (entidades crediticias, auditores, abogados, casinos,
  inmobiliarias, traficantes de arte)
- Controles internos AML
- Mensajes de Actividad Sospechosa (MAR/SAR)
- Registros de beneficiario real
"""

import argparse
import time
from datetime import UTC, datetime

from boe import _ensure_sync_log_table, log_sync
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# ---------------------------------------------------------------------------
# Seed data — PBC Obligated Subjects
# ---------------------------------------------------------------------------

SEED_PBC_OBLIGATED_SUBJECTS = [
    {
        "subject_type": "credit entity",
        "tin": "A28000001",
        "registration_number": "M-12345",
        "supervisory_authority": "Banco de Espana",
        "pbc_license": "PBC-2024-001",
        "status": "active",
    },
    {
        "subject_type": "PBC entity",
        "tin": "B56000002",
        "registration_number": "M-23456",
        "supervisory_authority": "CNMV",
        "pbc_license": "PBC-2024-002",
        "status": "active",
    },
    {
        "subject_type": "auditor",
        "tin": "C28000003",
        "registration_number": "N-34567",
        "supervisory_authority": "ICAC",
        "pbc_license": "PBC-2024-003",
        "status": "active",
    },
    {
        "subject_type": "lawyer",
        "tin": "D28000004",
        "registration_number": "C-45678",
        "supervisory_authority": "Colegio de Abogados de Madrid",
        "pbc_license": "PBC-2024-004",
        "status": "active",
    },
    {
        "subject_type": "casino",
        "tin": "E28000005",
        "registration_number": "J-56789",
        "supervisory_authority": "Junta Provincial de Juegos Madrid",
        "pbc_license": "PBC-2024-005",
        "status": "active",
    },
    {
        "subject_type": "real_estate_agency",
        "tin": "F28000006",
        "registration_number": "R-67890",
        "supervisory_authority": "Colegio de Agentes Inmobiliarios",
        "pbc_license": "PBC-2024-006",
        "status": "active",
    },
    {
        "subject_type": "art_dealer",
        "tin": "G28000007",
        "registration_number": "AD-78901",
        "supervisory_authority": "Ministerio de Cultura",
        "pbc_license": "PBC-2024-007",
        "status": "active",
    },
]

# ---------------------------------------------------------------------------
# Seed data — PBC Internal Controls
# ---------------------------------------------------------------------------

SEED_PBC_INTERNAL_CONTROLS = [
    {
        "obligated_subject_id": 1,
        "risk_assessment_date": "2024-06-15",
        "compliance_officer": "Dra. Ana Garcia",
        "internal_reporting_channel": True,
        "training_program": True,
        "audit_trail": True,
    },
    {
        "obligated_subject_id": 2,
        "risk_assessment_date": "2024-07-20",
        "compliance_officer": "Lic. Carlos Ruiz",
        "internal_reporting_channel": True,
        "training_program": False,
        "audit_trail": True,
    },
    {
        "obligated_subject_id": 4,
        "risk_assessment_date": "2024-08-10",
        "compliance_officer": "Dra. Maria Lopez",
        "internal_reporting_channel": True,
        "training_program": True,
        "audit_trail": False,
    },
]

# ---------------------------------------------------------------------------
# Seed data — Suspicious Activity Reports (SAR/MAR)
# ---------------------------------------------------------------------------

SEED_SUSPICIOUS_ACTIVITY_REPORTS = [
    {
        "obligated_subject_id": 1,
        "submission_date": "2024-09-01",
        "description": "Transacciones inusualmente grandes sin justificacion economica aparente.",
        "severity": "high",
        "status": "under_review",
        "sepblac_reference": "MAR-2024-001234",
    },
    {
        "obligated_subject_id": 3,
        "submission_date": "2024-10-15",
        "description": "Auditoria detecta discrepancias en libros contables de cliente.",
        "severity": "critical",
        "status": "filed",
        "sepblac_reference": "MAR-2024-005678",
    },
    {
        "obligated_subject_id": 5,
        "submission_date": "2024-11-20",
        "description": "Cliente intenta realizar pagos en efectivo por encima del limite legal.",
        "severity": "medium",
        "status": "investigated",
        "sepblac_reference": "MAR-2024-009012",
    },
]

# ---------------------------------------------------------------------------
# Seed data — Beneficial Owner Records
# ---------------------------------------------------------------------------

SEED_BENEFICIAL_OWNERS = [
    {
        "entity_id": 1,
        "owner_name": "Inversiones Ibericas S.A.",
        "ownership_percentage": 51.00,
        "acquisition_date": "2020-03-15",
        "verification_method": "certificado registry mercantil",
        "verification_date": "2024-01-10",
    },
    {
        "entity_id": 2,
        "owner_name": "Familia Rodriguez-Martinez",
        "ownership_percentage": 35.50,
        "acquisition_date": "2018-06-20",
        "verification_method": "escritura publicia",
        "verification_date": "2024-02-15",
    },
    {
        "entity_id": 4,
        "owner_name": "Dr. Javier Fernandez",
        "ownership_percentage": 100.00,
        "acquisition_date": "2015-01-10",
        "verification_method": "documento identidad",
        "verification_date": "2024-03-20",
    },
]


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------


def upsert_pbc_obligated_subject(conn, data):
    """Upsert a PBC obligated subject record."""
    conn.execute(
        text(
            """
            INSERT INTO pbc_obligated_subject
                (subject_type, tin, registration_number, supervisory_authority, pbc_license, status)
            VALUES
                (:subject_type, :tin, :registration_number, :supervisory_authority, :pbc_license, :status)
            ON CONFLICT (id) DO UPDATE SET
                subject_type = EXCLUDED.subject_type,
                tin = EXCLUDED.tin,
                registration_number = EXCLUDED.registration_number,
                supervisory_authority = EXCLUDED.supervisory_authority,
                pbc_license = EXCLUDED.pbc_license,
                status = EXCLUDED.status
            """
        ),
        data,
    )


def upsert_pbc_internal_control(conn, data):
    """Upsert a PBC internal control record."""
    conn.execute(
        text(
            """
            INSERT INTO pbc_internal_control
                (obligated_subject_id, risk_assessment_date, compliance_officer,
                 internal_reporting_channel, training_program, audit_trail)
            VALUES
                (:obligated_subject_id, :risk_assessment_date, :compliance_officer,
                 :internal_reporting_channel, :training_program, :audit_trail)
            ON CONFLICT (id) DO UPDATE SET
                obligated_subject_id = EXCLUDED.obligated_subject_id,
                risk_assessment_date = EXCLUDED.risk_assessment_date,
                compliance_officer = EXCLUDED.compliance_officer,
                internal_reporting_channel = EXCLUDED.internal_reporting_channel,
                training_program = EXCLUDED.training_program,
                audit_trail = EXCLUDED.audit_trail
            """
        ),
        data,
    )


def upsert_suspicious_activity_report(conn, data):
    """Upsert a suspicious activity report (SAR/MAR)."""
    conn.execute(
        text(
            """
            INSERT INTO suspicious_activity_report
                (obligated_subject_id, submission_date, description, severity, status, sepblac_reference)
            VALUES
                (:obligated_subject_id, :submission_date, :description, :severity, :status, :sepblac_reference)
            ON CONFLICT (id) DO UPDATE SET
                obligated_subject_id = EXCLUDED.obligated_subject_id,
                submission_date = EXCLUDED.submission_date,
                description = EXCLUDED.description,
                severity = EXCLUDED.severity,
                status = EXCLUDED.status,
                sepblac_reference = EXCLUDED.sepblac_reference
            """
        ),
        data,
    )


def upsert_beneficial_owner(conn, data):
    """Upsert a beneficial owner record."""
    conn.execute(
        text(
            """
            INSERT INTO beneficial_owner_record
                (entity_id, owner_name, ownership_percentage, acquisition_date,
                 verification_method, verification_date)
            VALUES
                (:entity_id, :owner_name, :ownership_percentage, :acquisition_date,
                 :verification_method, :verification_date)
            ON CONFLICT (id) DO UPDATE SET
                entity_id = EXCLUDED.entity_id,
                owner_name = EXCLUDED.owner_name,
                ownership_percentage = EXCLUDED.ownership_percentage,
                acquisition_date = EXCLUDED.acquisition_date,
                verification_method = EXCLUDED.verification_method,
                verification_date = EXCLUDED.verification_date
            """
        ),
        data,
    )


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def run_sync(worker_name: str = "cron-ley102010-weekly") -> dict:
    """Sync Ley 10/2010 PBC seed data into the database."""
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()

    total_rows = 0
    subjects_stored = 0
    controls_stored = 0
    reports_stored = 0
    owners_stored = 0

    try:
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)

            # PBC Obligated Subjects
            for data in SEED_PBC_OBLIGATED_SUBJECTS:
                upsert_pbc_obligated_subject(conn, data)
                total_rows += 1
                subjects_stored += 1

            # PBC Internal Controls
            for data in SEED_PBC_INTERNAL_CONTROLS:
                upsert_pbc_internal_control(conn, data)
                total_rows += 1
                controls_stored += 1

            # Suspicious Activity Reports
            for data in SEED_SUSPICIOUS_ACTIVITY_REPORTS:
                upsert_suspicious_activity_report(conn, data)
                total_rows += 1
                reports_stored += 1

            # Beneficial Owners
            for data in SEED_BENEFICIAL_OWNERS:
                upsert_beneficial_owner(conn, data)
                total_rows += 1
                owners_stored += 1

            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=total_rows,
                documentos_upserted=total_rows,
                started_at=sync_start,
            )

        return {
            "obligated_subjects": subjects_stored,
            "internal_controls": controls_stored,
            "suspicious_reports": reports_stored,
            "beneficial_owners": owners_stored,
        }

    except Exception as exc:
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                error_msg=str(exc),
                started_at=sync_start,
            )
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ley 10/2010 PBC worker: sync AML/PBC data"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run a single sync cycle and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles in continuous mode (default: {SYNC_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("ley102010")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-ley102010-weekly")
        print(
            f"[run-once] Subjects: {result['obligated_subjects']}, "
            f"Controls: {result['internal_controls']}, "
            f"Reports: {result['suspicious_reports']}, "
            f"Owners: {result['beneficial_owners']}"
        )
    else:
        print(f"Starting Ley 10/2010 PBC worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced subjects={result['obligated_subjects']}, "
                f"controls={result['internal_controls']}, "
                f"reports={result['suspicious_reports']}, "
                f"owners={result['beneficial_owners']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
