"""Worker para ingestion de datos Ley 11/2021 (Prevencion de Fraude).

Fase 31 — Expansion regulatoria.

Ingesta datos de:
- Programas de prevencion de fraude
- Evaluaciones de riesgo de fraude
- Incidentes de fraude
"""

import argparse
import logging
import time
from datetime import UTC, datetime

from boe import _ensure_sync_log_table, log_sync
from runtime import get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# ---------------------------------------------------------------------------
# Seed data — Fraud Prevention Programs
# ---------------------------------------------------------------------------

SEED_FRAUD_PREVENTION_PROGRAMS = [
    {
        "entity_id": 1,
        "code_of_conduct": True,
        "internal_reporting_system": True,
        "training_schedule": "Trimestral",
        "audit_frequency": "Semestral",
        "compliance_officer_name": "Dra. Ana Garcia",
        "status": "active",
    },
    {
        "entity_id": 2,
        "code_of_conduct": True,
        "internal_reporting_system": True,
        "training_schedule": "Anual",
        "audit_frequency": "Anual",
        "compliance_officer_name": "Lic. Carlos Ruiz",
        "status": "active",
    },
    {
        "entity_id": 4,
        "code_of_conduct": False,
        "internal_reporting_system": False,
        "training_schedule": None,
        "audit_frequency": None,
        "compliance_officer_name": "Dra. Maria Lopez",
        "status": "inactive",
    },
]

# ---------------------------------------------------------------------------
# Seed data — Fraud Risk Assessments
# ---------------------------------------------------------------------------

SEED_FRAUD_RISK_ASSESSMENTS = [
    {
        "entity_id": 1,
        "assessment_date": "2024-06-15",
        "risk_areas": '["financial reporting", "procurement", "related party transactions"]',
        "mitigation_measures": "Segregacion de funciones, aprobaciones multinivel, auditoria interna",
        "next_review_date": "2024-12-15",
    },
    {
        "entity_id": 2,
        "assessment_date": "2024-08-20",
        "risk_areas": '["expense reimbursement", "vendor management"]',
        "mitigation_measures": "Validacion automatica de facturas, lista blanca de proveedores",
        "next_review_date": "2025-02-20",
    },
]

# ---------------------------------------------------------------------------
# Seed data — Fraud Incidents
# ---------------------------------------------------------------------------

SEED_FRAUD_INCIDENTS = [
    {
        "entity_id": 1,
        "incident_date": "2024-09-01",
        "description": "Deteccion de facturas ficticias emitidas por proveedor relacionado.",
        "amount_eur": 45000.00,
        "status": "resolved",
        "resolution_date": "2024-11-15",
        "regulatory_notification": True,
    },
    {
        "entity_id": 2,
        "incident_date": "2024-10-15",
        "description": "Desviacion de fondos mediante manipulacion de pagos a empleados fantasmas.",
        "amount_eur": 120000.00,
        "status": "under_investigation",
        "resolution_date": None,
        "regulatory_notification": True,
    },
    {
        "entity_id": 3,
        "incident_date": "2024-12-01",
        "description": "Manipulacion de estados financieros para inflar ingresos del trimestre.",
        "amount_eur": 250000.00,
        "status": "open",
        "resolution_date": None,
        "regulatory_notification": False,
    },
]


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------


def upsert_fraud_prevention_program(conn, data):
    """Upsert a fraud prevention program."""
    conn.execute(
        text(
            """
            INSERT INTO fraud_prevention_program
                (entity_id, code_of_conduct, internal_reporting_system,
                 training_schedule, audit_frequency, compliance_officer_name, status)
            VALUES
                (:entity_id, :code_of_conduct, :internal_reporting_system,
                 :training_schedule, :audit_frequency, :compliance_officer_name, :status)
            ON CONFLICT (id) DO UPDATE SET
                entity_id = EXCLUDED.entity_id,
                code_of_conduct = EXCLUDED.code_of_conduct,
                internal_reporting_system = EXCLUDED.internal_reporting_system,
                training_schedule = EXCLUDED.training_schedule,
                audit_frequency = EXCLUDED.audit_frequency,
                compliance_officer_name = EXCLUDED.compliance_officer_name,
                status = EXCLUDED.status
            """
        ),
        data,
    )


def upsert_fraud_risk_assessment(conn, data):
    """Upsert a fraud risk assessment."""
    conn.execute(
        text(
            """
            INSERT INTO fraud_risk_assessment
                (entity_id, assessment_date, risk_areas, mitigation_measures, next_review_date)
            VALUES
                (:entity_id, :assessment_date, :risk_areas, :mitigation_measures, :next_review_date)
            ON CONFLICT (id) DO UPDATE SET
                entity_id = EXCLUDED.entity_id,
                assessment_date = EXCLUDED.assessment_date,
                risk_areas = EXCLUDED.risk_areas,
                mitigation_measures = EXCLUDED.mitigation_measures,
                next_review_date = EXCLUDED.next_review_date
            """
        ),
        data,
    )


def upsert_fraud_incident(conn, data):
    """Upsert a fraud incident."""
    conn.execute(
        text(
            """
            INSERT INTO fraud_incident
                (entity_id, incident_date, description, amount_eur, status,
                 resolution_date, regulatory_notification)
            VALUES
                (:entity_id, :incident_date, :description, :amount_eur, :status,
                 :resolution_date, :regulatory_notification)
            ON CONFLICT (id) DO UPDATE SET
                entity_id = EXCLUDED.entity_id,
                incident_date = EXCLUDED.incident_date,
                description = EXCLUDED.description,
                amount_eur = EXCLUDED.amount_eur,
                status = EXCLUDED.status,
                resolution_date = EXCLUDED.resolution_date,
                regulatory_notification = EXCLUDED.regulatory_notification
            """
        ),
        data,
    )


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def run_sync(worker_name: str = "cron-ley112021-weekly") -> dict:
    """Sync Ley 11/2021 antifraud seed data into the database."""
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()

    total_rows = 0
    programs_stored = 0
    assessments_stored = 0
    incidents_stored = 0

    try:
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)

            # Fraud Prevention Programs
            for data in SEED_FRAUD_PREVENTION_PROGRAMS:
                upsert_fraud_prevention_program(conn, data)
                total_rows += 1
                programs_stored += 1

            # Fraud Risk Assessments
            for data in SEED_FRAUD_RISK_ASSESSMENTS:
                upsert_fraud_risk_assessment(conn, data)
                total_rows += 1
                assessments_stored += 1

            # Fraud Incidents
            for data in SEED_FRAUD_INCIDENTS:
                upsert_fraud_incident(conn, data)
                total_rows += 1
                incidents_stored += 1

            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=total_rows,
                documentos_upserted=total_rows,
                started_at=sync_start,
            )

        return {
            "programs": programs_stored,
            "assessments": assessments_stored,
            "incidents": incidents_stored,
        }

    except Exception as exc:
        entity_id = "fraud"
        if not handle_worker_failure(engine, "fraud", entity_id, "sync_entity", exc):
            logger.warning("Entity fraud moved to dead-letter")
            return {"programs": 0, "assessments": 0, "incidents": 0}
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
        description="Ley 11/2021 antifraud worker: sync fraud prevention data"
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
    init_sentry("ley112021")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-ley112021-weekly")
        print(
            f"[run-once] Programs: {result['programs']}, "
            f"Assessments: {result['assessments']}, "
            f"Incidents: {result['incidents']}"
        )
    else:
        print(f"Starting Ley 11/2021 antifraud worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced programs={result['programs']}, "
                f"assessments={result['assessments']}, "
                f"incidents={result['incidents']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
