"""CSRD (Corporate Sustainability Reporting Directive) worker.

Fase 31.9.2 — Expansion regulatoria: CSRD.

Ingests CSRD sustainability reports, ESG data points, ES standards
and double materiality assessments from ESAP sources.

Usage:
    python corporate_sustainability.py --run-once
    python corporate_sustainability.py --interval 3600
"""

import argparse
import logging
import time

from boe import log_sync
from change_detection import ensure_source_revision_table
from runtime import ensure_database_connection, get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


# ---------------------------------------------------------------------------
# Seed data — realistic CSRD fixtures
# ---------------------------------------------------------------------------

CSRD_SEED_REPORTS = [
    {
        "entity_id": 101,
        "reporting_year": 2024,
        "esap_url": "https://www.esap.europa.eu/content/acme-corp-sustainability-report-2024.pdf",
        "assurance_status": "limited",
        "reporting_standard": "ESGAS",
        "status": "published",
    },
    {
        "entity_id": 102,
        "reporting_year": 2024,
        "esap_url": "https://www.esap.europa.eu/content/iberia-group-esg-report-2024.pdf",
        "assurance_status": "reasonable",
        "reporting_standard": "ESGAS",
        "status": "published",
    },
    {
        "entity_id": 103,
        "reporting_year": 2023,
        "esap_url": "https://www.esap.europa.eu/content/telefonica-sustainability-2023.pdf",
        "assurance_status": "limited",
        "reporting_standard": "ESGAS",
        "status": "published",
    },
    {
        "entity_id": 101,
        "reporting_year": 2023,
        "esap_url": "https://www.esap.europa.eu/content/acme-corp-sustainability-2023.pdf",
        "assurance_status": "none",
        "reporting_standard": "national",
        "status": "published",
    },
]

CSRD_SEED_ESG_DATA = [
    # ACME Corp 2024 (report_id=1)
    {"report_id": 1, "topic": "environment", "indicator_code": "ESRS E1-10", "value": 12500.0, "unit": "tCO2e", "scope": 1, "verification_status": "verified"},
    {"report_id": 1, "topic": "environment", "indicator_code": "ESRS E1-11", "value": 45000.0, "unit": "tCO2e", "scope": 2, "verification_status": "verified"},
    {"report_id": 1, "topic": "environment", "indicator_code": "ESRS E1-12", "value": 120000.0, "unit": "tCO2e", "scope": 3, "verification_status": "limited"},
    {"report_id": 1, "topic": "environment", "indicator_code": "ESRS E2-10", "value": 85.0, "unit": "%", "scope": None, "verification_status": "verified"},
    {"report_id": 1, "topic": "social", "indicator_code": "ESRS S1-10", "value": 15200.0, "unit": "headcount", "scope": None, "verification_status": "verified"},
    {"report_id": 1, "topic": "social", "indicator_code": "ESRS S1-15", "value": 42.5, "unit": "%", "scope": None, "verification_status": "verified"},
    {"report_id": 1, "topic": "governance", "indicator_code": "ESRS G1-10", "value": 3.2, "unit": "%", "scope": None, "verification_status": "limited"},
    # Iberia Group 2024 (report_id=2)
    {"report_id": 2, "topic": "environment", "indicator_code": "ESRS E1-10", "value": 8200.0, "unit": "tCO2e", "scope": 1, "verification_status": "verified"},
    {"report_id": 2, "topic": "environment", "indicator_code": "ESRS E1-11", "value": 2100.0, "unit": "tCO2e", "scope": 2, "verification_status": "verified"},
    {"report_id": 2, "topic": "environment", "indicator_code": "ESRS E1-12", "value": 65000.0, "unit": "tCO2e", "scope": 3, "verification_status": "limited"},
    {"report_id": 2, "topic": "social", "indicator_code": "ESRS S1-10", "value": 32000.0, "unit": "headcount", "scope": None, "verification_status": "verified"},
    # Telefonica 2023 (report_id=3)
    {"report_id": 3, "topic": "environment", "indicator_code": "ESRS E1-10", "value": 18500.0, "unit": "tCO2e", "scope": 1, "verification_status": "verified"},
    {"report_id": 3, "topic": "environment", "indicator_code": "ESRS E1-11", "value": 9200.0, "unit": "tCO2e", "scope": 2, "verification_status": "verified"},
    {"report_id": 3, "topic": "social", "indicator_code": "ESRS S1-10", "value": 115000.0, "unit": "headcount", "scope": None, "verification_status": "verified"},
]

CSRD_SEED_ES = [
    {"standard_code": "ESRS E1", "topic": "Climate change", "applicable_from_year": 2024, "description": "Emission of greenhouse gases, energy use, water and marine resources, biodiversity and ecosystems, circular economy", "status": "active"},
    {"standard_code": "ESRS E2", "topic": "Pollution", "applicable_from_year": 2025, "description": "Pollution prevention and control, air quality, water and soil pollution, waste", "status": "active"},
    {"standard_code": "ESRS E3", "topic": "Water and marine resources", "applicable_from_year": 2025, "description": "Water withdrawals, water discharges, water and marine ecosystems", "status": "active"},
    {"standard_code": "ESRS E4", "topic": "Biodiversity and ecosystems", "applicable_from_year": 2025, "description": "Biodiversity protection, land use, ecosystems and species", "status": "active"},
    {"standard_code": "ESRS E5", "topic": "Resource use and circular economy", "applicable_from_year": 2025, "description": "Raw material use, energy circular, waste circular, packaging", "status": "active"},
    {"standard_code": "ESRS S1", "topic": "Own workforce", "applicable_from_year": 2024, "description": "Working conditions, social dialogue, health and safety, diversity and equal treatment", "status": "active"},
    {"standard_code": "ESRS S2", "topic": "Workers in the value chain", "applicable_from_year": 2025, "description": "Workers in value chain, collective bargaining, grievance mechanisms", "status": "active"},
    {"standard_code": "ESRS S3", "topic": "Affected communities", "applicable_from_year": 2025, "description": "Community health, safety, living income, cultural heritage", "status": "active"},
    {"standard_code": "ESRS S4", "topic": "Value chain workers", "applicable_from_year": 2026, "description": "SME workers in value chain, access to remedy", "status": "active"},
    {"standard_code": "ESRS G1", "topic": "Business conduct", "applicable_from_year": 2024, "description": "Anti-corruption, anti-bribery, governance structure, conduct programmes", "status": "active"},
]

CSRD_SEED_MATERIALITY = [
    {
        "entity_id": 101,
        "impact_materiality": {
            "assessed": True,
            "significant_impacts": ["GHG emissions", "waste generation", "water consumption"],
            "significant_dependencies": ["raw materials", "skilled workforce"],
        },
        "financial_materiality": {
            "assessed": True,
            "material_risks": ["carbon pricing", "regulatory fines"],
            "material_opportunities": ["energy efficiency", "circular economy"],
        },
        "assessment_date": "2024-06-15",
        "key_impacts": "GHG emissions (Scope 1-3), waste to landfill, water withdrawal",
        "key_dependencies": "Raw material supply chain, skilled labor availability",
        "status": "published",
    },
    {
        "entity_id": 102,
        "impact_materiality": {
            "assessed": True,
            "significant_impacts": ["aviation emissions", "waste"],
            "significant_dependencies": ["fuel supply", "airport infrastructure"],
        },
        "financial_materiality": {
            "assessed": True,
            "material_risks": ["fuel price volatility", "carbon taxes"],
            "material_opportunities": ["SAF adoption", "fleet efficiency"],
        },
        "assessment_date": "2024-07-01",
        "key_impacts": "CO2 emissions from flights, in-flight waste, noise pollution",
        "key_dependencies": "Aviation fuel supply, airport slot availability",
        "status": "published",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_csrd_tables(conn):
    """Ensure CSRD tables exist (defensive — migration should have created them)."""
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'csrd_entity_report'
            ) THEN
                RAISE EXCEPTION 'csrd_entity_report table missing — run Alembic migration first';
            END IF;
        END $$;
    """))


# ---------------------------------------------------------------------------
# Upsert functions
# ---------------------------------------------------------------------------


def upsert_csrd_entity_report(conn, payload: dict) -> int:
    """Upsert CSRD entity report. Returns report id."""
    result = conn.execute(
        text("""
            INSERT INTO csrd_entity_report
                (entity_id, reporting_year, esap_url, assurance_status,
                 reporting_standard, status, created_at)
            VALUES
                (:entity_id, :year, :esap_url, :assurance, :standard, :status, now())
            ON CONFLICT DO NOTHING
            RETURNING id
        """),
        {
            "entity_id": payload["entity_id"],
            "year": payload["reporting_year"],
            "esap_url": payload.get("esap_url"),
            "assurance": payload.get("assurance_status"),
            "standard": payload.get("reporting_standard"),
            "status": payload.get("status", "draft"),
        },
    ).mappings().first()

    if result:
        return result["id"]

    # Already exists — find by entity_id + reporting_year
    existing = conn.execute(
        text("""
            SELECT id FROM csrd_entity_report
            WHERE entity_id = :entity_id AND reporting_year = :year
        """),
        {"entity_id": payload["entity_id"], "year": payload["reporting_year"]},
    ).mappings().first()

    if existing:
        return existing["id"]

    # Fallback: insert without conflict resolution
    conn.execute(
        text("""
            INSERT INTO csrd_entity_report
                (entity_id, reporting_year, esap_url, assurance_status,
                 reporting_standard, status, created_at)
            VALUES
                (:entity_id, :year, :esap_url, :assurance, :standard, :status, now())
        """),
        {
            "entity_id": payload["entity_id"],
            "year": payload["reporting_year"],
            "esap_url": payload.get("esap_url"),
            "assurance": payload.get("assurance_status"),
            "standard": payload.get("reporting_standard"),
            "status": payload.get("status", "draft"),
        },
    )
    return conn.execute(
        text("""
            SELECT id FROM csrd_entity_report
            WHERE entity_id = :entity_id AND reporting_year = :year
            ORDER BY id DESC LIMIT 1
        """),
        {"entity_id": payload["entity_id"], "year": payload["reporting_year"]},
    ).mappings().first()["id"]


def upsert_csrd_esg_data_point(conn, payload: dict):
    """Upsert ESG data point."""
    conn.execute(
        text("""
            INSERT INTO csrd_esg_data_point
                (report_id, topic, indicator_code, value, unit, scope,
                 verification_status, created_at)
            VALUES
                (:report_id, :topic, :code, :value, :unit, :scope,
                 :verification, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "report_id": payload["report_id"],
            "topic": payload["topic"],
            "code": payload.get("indicator_code"),
            "value": payload.get("value"),
            "unit": payload.get("unit"),
            "scope": payload.get("scope"),
            "verification": payload.get("verification_status"),
        },
    )


def upsert_csrd_ess(conn, payload: dict):
    """Upsert ES standard."""
    conn.execute(
        text("""
            INSERT INTO csrd_ess
                (standard_code, topic, applicable_from_year, description, status, created_at)
            VALUES
                (:code, :topic, :from_year, :desc, :status, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "code": payload["standard_code"],
            "topic": payload.get("topic"),
            "from_year": payload.get("applicable_from_year"),
            "desc": payload.get("description"),
            "status": payload.get("status", "active"),
        },
    )


def upsert_csrd_double_materiality(conn, payload: dict):
    """Upsert double materiality assessment."""
    conn.execute(
        text("""
            INSERT INTO csrd_double_materiality
                (entity_id, impact_materiality, financial_materiality,
                 assessment_date, key_impacts, key_dependencies, status, created_at)
            VALUES
                (:entity_id, :impact::jsonb, :financial::jsonb, :assess_date,
                 :impacts, :deps, :status, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "entity_id": payload["entity_id"],
            "impact": str(payload.get("impact_materiality")) if payload.get("impact_materiality") else None,
            "financial": str(payload.get("financial_materiality")) if payload.get("financial_materiality") else None,
            "assess_date": payload.get("assessment_date"),
            "impacts": payload.get("key_impacts"),
            "deps": payload.get("key_dependencies"),
            "status": payload.get("status", "draft"),
        },
    )


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def run_sync(worker_name: str = "cron-csrd-weekly"):
    """Run CSRD sync cycle."""
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    ensure_database_connection(engine)
    sync_start = time.time()
    processed = 0
    stored = 0

    try:
        with engine.begin() as conn:
            _ensure_csrd_tables(conn)
            ensure_source_revision_table(conn)

            # Seed entity reports
            for report in CSRD_SEED_REPORTS:
                try:
                    report_id = upsert_csrd_entity_report(conn, report)
                    processed += 1

                    # Seed ESG data points for this report
                    data_points = [d for d in CSRD_SEED_ESG_DATA if d["report_id"] == report_id]
                    for dp in data_points:
                        upsert_csrd_esg_data_point(conn, dp)
                        stored += 1

                except Exception:
                    logger.exception("Error processing report %s", report.get("reporting_year"))

            # Seed ES standards
            for ess in CSRD_SEED_ES:
                try:
                    upsert_csrd_ess(conn, ess)
                    stored += 1
                except Exception:
                    logger.exception("Error processing ES standard %s", ess.get("standard_code"))

            # Seed double materiality
            for dm in CSRD_SEED_MATERIALITY:
                try:
                    upsert_csrd_double_materiality(conn, dm)
                    processed += 1
                    stored += 1
                except Exception:
                    logger.exception("Error processing materiality assessment %s", dm.get("entity_id"))

            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=processed,
                documentos_upserted=stored,
                started_at=sync_start,
            )

        return {"processed": processed, "stored": stored}
    except Exception as exc:
        entity_id = "corporate_sustainability"
        if not handle_worker_failure(engine, "corporate_sustainability", entity_id, "sync_entity", exc):
            logger.warning("Entity corporate_sustainability moved to dead-letter")
            return {"processed": 0, "stored": 0}
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                documentos_processed=processed,
                documentos_upserted=stored,
                error_msg=str(exc),
                started_at=sync_start,
            )
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CSRD worker: sync corporate sustainability reporting data"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run a single sync cycle and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles (default: {SYNC_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("csrd")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-csrd-weekly")
        print(f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}")
    else:
        while True:
            try:
                result = run_sync(worker_name="cron-csrd-weekly")
                print(f"[sync] Procesados: {result['processed']}, Almacenados: {result['stored']}")
            except Exception:
                logger.exception("CSRD sync failed")
            time.sleep(interval)
