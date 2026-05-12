"""SFDR (Sustainable Finance Disclosure Regulation) worker.

Fase 31.9.1 — Expansion regulatoria: SFDR.

Ingests SFDR product data, PCAI indicators, pre-contractual documents
and annual reports from ESAP and CNMV sources.

Usage:
    python sustainable_finance.py --run-once
    python sustainable_finance.py --interval 3600
"""

import argparse
import logging
import os
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

# ESAP (European Single Access Point) — SFDR disclosures
ESAP_SFDR_URLS = [
    "https://www.esap-finance.eu/search?q=sfdr",
]

# Seed URLs for SFDR product data
SEED_URLS = [u for u in os.getenv("SFDR_SEED_URLS", "").split(",") if u.strip()] or ESAP_SFDR_URLS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_sfdr_tables(conn):
    """Ensure SFDR tables exist (defensive — migration should have created them)."""
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'sfdr_product'
            ) THEN
                RAISE EXCEPTION 'sfdr_product table missing — run Alembic migration first';
            END IF;
        END $$;
    """))


# ---------------------------------------------------------------------------
# Seed data — realistic SFDR product fixtures
# ---------------------------------------------------------------------------

SFDR_SEED_DATA = [
    {
        "product_name": "Green Equity Fund SRI",
        "product_type": "art-8",
        "sustainability_strategy": "Inversion sostenible con criterios ESG integrados",
        "principal_adverse_impact": "true",
        "paci_aggregated": {"sa_1_co2": 150.5, "sa_2_carbon_intensity": 85.2},
        "paci_detailed_url": "https://www.esap-finance.eu/sfdr/paci/green-equity-sri",
        "distribution_country": ["ES", "FR", "DE", "PT"],
        "status": "active",
    },
    {
        "product_name": "EU Climate Transition ETF",
        "product_type": "art-8",
        "sustainability_strategy": "Indice alineado con transicion climatica EU",
        "principal_adverse_impact": "true",
        "paci_aggregated": {"sa_1_co2": 95.0, "sa_3_fossil": 0.05},
        "paci_detailed_url": "https://www.esap-finance.eu/sfdr/paci/climate-transition-etf",
        "distribution_country": ["ES", "DE", "NL", "BE"],
        "status": "active",
    },
    {
        "product_name": "Global Impact Fund",
        "product_type": "art-9",
        "sustainability_strategy": "Inversion de impacto con objetivos ODS",
        "principal_adverse_impact": "true",
        "paci_aggregated": {"sa_1_co2": 50.0, "sa_5_water": 0.02},
        "paci_detailed_url": "https://www.esap-finance.eu/sfdr/paci/global-impact",
        "distribution_country": ["ES", "FR", "IT", "PT"],
        "status": "active",
    },
    {
        "product_name": "ESR Equities Europe",
        "product_type": "art-8",
        "sustainability_strategy": "Acciones Europa con consideracion PCAI",
        "principal_adverse_impact": "true",
        "paci_aggregated": {"sa_1_co2": 120.0},
        "paci_detailed_url": "https://www.esap-finance.eu/sfdr/paci/esr-europe",
        "distribution_country": ["ES", "FR", "DE"],
        "status": "active",
    },
    {
        "product_name": "Standard Euro Bond Fund",
        "product_type": "art-6",
        "sustainability_strategy": None,
        "principal_adverse_impact": "false",
        "paci_aggregated": None,
        "paci_detailed_url": None,
        "distribution_country": ["ES"],
        "status": "active",
    },
]

SFDR_PACAI_INDICATORS = [
    # Green Equity Fund SRI (product_id=1)
    {"product_id": 1, "indicator_code": "sa.1", "indicator_name": "Greenhouse gas emissions", "value": 150.5, "unit": "tCO2e", "reference_period": "2024", "methodology": "Scope 1+2", "status": "active"},
    {"product_id": 1, "indicator_code": "sa.2", "indicator_name": "Carbon footprint", "value": 85.2, "unit": "tCO2e/M EUR", "reference_period": "2024", "methodology": "Total portfolio", "status": "active"},
    {"product_id": 1, "indicator_code": "sa.4", "indicator_name": "Exposure to companies involved in fossil gas", "value": 0.02, "unit": "% NAV", "reference_period": "2024", "methodology": "Revenue threshold 1%", "status": "active"},
    # EU Climate Transition ETF (product_id=2)
    {"product_id": 2, "indicator_code": "sa.1", "indicator_name": "Greenhouse gas emissions", "value": 95.0, "unit": "tCO2e", "reference_period": "2024", "methodology": "Scope 1+2", "status": "active"},
    {"product_id": 2, "indicator_code": "sa.3", "indicator_name": "Fossil gas exposure", "value": 0.05, "unit": "% NAV", "reference_period": "2024", "methodology": "Revenue threshold", "status": "active"},
    # Global Impact Fund (product_id=3)
    {"product_id": 3, "indicator_code": "sa.1", "indicator_name": "Greenhouse gas emissions", "value": 50.0, "unit": "tCO2e", "reference_period": "2024", "methodology": "Scope 1+2+3", "status": "active"},
    {"product_id": 3, "indicator_code": "sa.5", "indicator_name": "Water emission", "value": 0.02, "unit": "% NAV", "reference_period": "2024", "methodology": "Direct discharge", "status": "active"},
    # ESR Equities Europe (product_id=4)
    {"product_id": 4, "indicator_code": "sa.1", "indicator_name": "Greenhouse gas emissions", "value": 120.0, "unit": "tCO2e", "reference_period": "2024", "methodology": "Scope 1+2", "status": "active"},
]

SFDR_PRE_CONTRACTUAL = [
    {"product_id": 1, "document_type": "KID", "url": "https://www.esap-finance.eu/documents/green-equity-sri-kid.pdf", "published_date": "2024-01-15", "version": "2024.1", "status": "active"},
    {"product_id": 1, "document_type": "PPI", "url": "https://www.esap-finance.eu/documents/green-equity-sri-ppi.pdf", "published_date": "2024-01-15", "version": "2024.1", "status": "active"},
    {"product_id": 3, "document_type": "KID", "url": "https://www.esap-finance.eu/documents/global-impact-kid.pdf", "published_date": "2024-02-01", "version": "2024.1", "status": "active"},
    {"product_id": 3, "document_type": "prospectus", "url": "https://www.esap-finance.eu/documents/global-impact-prospectus.pdf", "published_date": "2024-02-01", "version": "2024.1", "status": "active"},
    {"product_id": 2, "document_type": "KID", "url": "https://www.esap-finance.eu/documents/climate-transition-kid.pdf", "published_date": "2024-03-01", "version": "2024.1", "status": "active"},
]

SFDR_ANNUAL_REPORTS = [
    {"entity_id": 1, "reporting_year": 2024, "paci_results": {"sa_1_met": True, "sa_2_met": True, "sa_3_not_applicable": True}, "engagement_activities": "Active engagement with portfolio companies on Scope 3 reduction", "good_practice_examples": "Carbon offset program for high-emission holdings", "url": "https://www.esap-finance.eu/reports/sfdr-2024-entity-1.pdf", "published_date": "2025-03-31", "status": "published"},
    {"entity_id": 2, "reporting_year": 2024, "paci_results": {"sa_1_met": True, "sa_3_met": True}, "engagement_activities": "Climate transition alignment monitoring", "good_practice_examples": "Net-zero benchmark tracking", "url": "https://www.esap-finance.eu/reports/sfdr-2024-entity-2.pdf", "published_date": "2025-04-15", "status": "published"},
]


# ---------------------------------------------------------------------------
# Upsert functions
# ---------------------------------------------------------------------------


def upsert_sfdr_product(conn, payload: dict) -> int:
    """Upsert SFDR product. Returns product id."""
    product_name = payload["product_name"]
    existing = conn.execute(
        text("SELECT id FROM sfdr_product WHERE product_name = :name"),
        {"name": product_name},
    ).mappings().first()

    if existing:
        conn.execute(
            text("""
                UPDATE sfdr_product SET
                    product_type = :product_type,
                    sustainability_strategy = :strategy,
                    principal_adverse_impact = :paci,
                    paci_aggregated = :paci_agg::jsonb,
                    paci_detailed_url = :paci_url,
                    distribution_country = :dist::jsonb,
                    status = :status,
                    created_at = now()
                WHERE product_name = :name
            """),
            {
                "name": product_name,
                "product_type": payload["product_type"],
                "strategy": payload.get("sustainability_strategy"),
                "paci": payload.get("principal_adverse_impact"),
                "paci_agg": str(payload.get("paci_aggregated")) if payload.get("paci_aggregated") else None,
                "paci_url": payload.get("paci_detailed_url"),
                "dist": str(payload.get("distribution_country")) if payload.get("distribution_country") else None,
                "status": payload.get("status", "active"),
            },
        )
        return existing["id"]

    result = conn.execute(
        text("""
            INSERT INTO sfdr_product
                (product_name, product_type, sustainability_strategy,
                 principal_adverse_impact, paci_aggregated, paci_detailed_url,
                 distribution_country, status, created_at)
            VALUES
                (:name, :ptype, :strategy, :paci, :paci_agg::jsonb, :paci_url,
                 :dist::jsonb, :status, now())
            RETURNING id
        """),
        {
            "name": product_name,
            "ptype": payload["product_type"],
            "strategy": payload.get("sustainability_strategy"),
            "paci": payload.get("principal_adverse_impact"),
            "paci_agg": str(payload.get("paci_aggregated")) if payload.get("paci_aggregated") else None,
            "paci_url": payload.get("paci_detailed_url"),
            "dist": str(payload.get("distribution_country")) if payload.get("distribution_country") else None,
            "status": payload.get("status", "active"),
        },
    ).mappings()
    return result.fetchone()["id"]


def upsert_sfdr_pacai_indicator(conn, payload: dict):
    """Upsert PCAI indicator."""
    conn.execute(
        text("""
            INSERT INTO sfdr_paci_indicator
                (product_id, indicator_code, indicator_name, value, unit,
                 reference_period, methodology, status, created_at)
            VALUES
                (:product_id, :code, :name, :value, :unit,
                 :ref_period, :methodology, :status, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "product_id": payload["product_id"],
            "code": payload["indicator_code"],
            "name": payload["indicator_name"],
            "value": payload.get("value"),
            "unit": payload.get("unit"),
            "ref_period": payload.get("reference_period"),
            "methodology": payload.get("methodology"),
            "status": payload.get("status", "active"),
        },
    )


def upsert_sfdr_pre_contractual(conn, payload: dict):
    """Upsert pre-contractual document."""
    conn.execute(
        text("""
            INSERT INTO sfdr_pre_contractual
                (product_id, document_type, url, published_date, version, status, created_at)
            VALUES
                (:product_id, :doc_type, :url, :pub_date, :version, :status, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "product_id": payload["product_id"],
            "doc_type": payload["document_type"],
            "url": payload.get("url"),
            "pub_date": payload.get("published_date"),
            "version": payload.get("version"),
            "status": payload.get("status", "active"),
        },
    )


def upsert_sfdr_annual_report(conn, payload: dict):
    """Upsert annual SFDR report."""
    conn.execute(
        text("""
            INSERT INTO sfdr_annual_report
                (entity_id, reporting_year, paci_results, engagement_activities,
                 good_practice_examples, url, published_date, status, created_at)
            VALUES
                (:entity_id, :year, :paci::jsonb, :engagement, :examples,
                 :url, :pub_date, :status, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "entity_id": payload["entity_id"],
            "year": payload["reporting_year"],
            "paci": str(payload.get("paci_results")) if payload.get("paci_results") else None,
            "engagement": payload.get("engagement_activities"),
            "examples": payload.get("good_practice_examples"),
            "url": payload.get("url"),
            "pub_date": payload.get("published_date"),
            "status": payload.get("status", "draft"),
        },
    )


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def run_sync(worker_name: str = "cron-sfdr-weekly"):
    """Run SFDR sync cycle."""
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    ensure_database_connection(engine)
    sync_start = time.time()
    processed = 0
    stored = 0

    try:
        with engine.begin() as conn:
            _ensure_sfdr_tables(conn)
            ensure_source_revision_table(conn)

            # Seed SFDR products
            for product in SFDR_SEED_DATA:
                try:
                    product_id = upsert_sfdr_product(conn, product)
                    processed += 1

                    # Seed PCAI indicators for this product
                    indicators = [i for i in SFDR_PACAI_INDICATORS if i["product_id"] == product_id]
                    for indicator in indicators:
                        upsert_sfdr_pacai_indicator(conn, indicator)
                        stored += 1

                    # Seed pre-contractual docs
                    docs = [d for d in SFDR_PRE_CONTRACTUAL if d["product_id"] == product_id]
                    for doc in docs:
                        upsert_sfdr_pre_contractual(conn, doc)
                        stored += 1

                except Exception:
                    logger.exception("Error processing product %s", product.get("product_name"))

            # Seed annual reports
            for report in SFDR_ANNUAL_REPORTS:
                try:
                    upsert_sfdr_annual_report(conn, report)
                    processed += 1
                    stored += 1
                except Exception:
                    logger.exception("Error processing annual report %s", report.get("reporting_year"))

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
        entity_id = "sustainable_finance"
        if not handle_worker_failure(engine, "sustainable_finance", entity_id, "sync_entity", exc):
            logger.warning("Entity sustainable_finance moved to dead-letter")
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
        description="SFDR worker: sync sustainable finance disclosure data"
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
    init_sentry("sfdr")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-sfdr-weekly")
        print(f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}")
    else:
        while True:
            try:
                result = run_sync(worker_name="cron-sfdr-weekly")
                print(f"[sync] Procesados: {result['processed']}, Almacenados: {result['stored']}")
            except Exception:
                logger.exception("SFDR sync failed")
            time.sleep(interval)
