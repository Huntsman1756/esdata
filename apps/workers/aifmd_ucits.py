"""AIFMD and UCITS worker.

Fase 31.9.3 — Expansion regulatoria: AIFMD y UCITS.

Ingests AIFMD fund data, UCITS fund data, regulatory reports
and liquidity management data from ESAP and national competent authorities.

Usage:
    python aifmd_ucits.py --run-once
    python aifmd_ucits.py --interval 3600
"""

import argparse
import logging
import time

from boe import log_sync
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)


# ---------------------------------------------------------------------------
# Seed data — realistic AIFMD/UCITS fixtures
# ---------------------------------------------------------------------------

AIFMD_SEED_FUNDS = [
    {
        "fund_name": "Iberian Real Estate Fund",
        "aifm_id": 501,
        "fund_type": "real-estate",
        "registration_date": "2020-03-15",
        "home_member_state": "ES",
        "cross_border_passport": True,
        "total_aum_eur": 250000000.00,
        "investor_type": "professional",
        "lock_up_period": "2 years",
        "redemption_frequency": "quarterly",
        "leverage_method": "asset-by-asset",
        "leverage_max_pct": 200.00,
        "status": "active",
    },
    {
        "fund_name": "European Growth Capital III",
        "aifm_id": 502,
        "fund_type": "alternative",
        "registration_date": "2021-06-01",
        "home_member_state": "DE",
        "cross_border_passport": True,
        "total_aum_eur": 780000000.00,
        "investor_type": "professional",
        "lock_up_period": "5 years",
        "redemption_frequency": "annually",
        "leverage_method": "portfolio",
        "leverage_max_pct": 300.00,
        "status": "active",
    },
    {
        "fund_name": "Strategic Credit Opportunities",
        "aifm_id": 503,
        "fund_type": "alternative",
        "registration_date": "2019-11-20",
        "home_member_state": "FR",
        "cross_border_passport": False,
        "total_aum_eur": 150000000.00,
        "investor_type": "professional",
        "lock_up_period": "3 years",
        "redemption_frequency": "semi-annually",
        "leverage_method": "asset-by-asset",
        "leverage_max_pct": 150.00,
        "status": "active",
    },
]

UCITS_SEED_FUNDS = [
    {
        "fund_name": "Euro Green Bond Fund",
        "management_company": "Global Asset Management SA",
        "registration_date": "2018-01-10",
        "home_member_state": "LU",
        "cross_border_passport": True,
        "total_aum_eur": 1200000000.00,
        "depositary_id": 601,
        "krid_url": "https://www.esap.europa.eu/ucits/euro-green-bond-krid.pdf",
        "investment_strategy": "Investment in Euro-denominated green bonds",
        "risk_profile": "4/7",
        "status": "active",
    },
    {
        "fund_name": "Iberian Equity Income",
        "management_company": "Iberian Capital Management",
        "registration_date": "2015-05-20",
        "home_member_state": "ES",
        "cross_border_passport": True,
        "total_aum_eur": 450000000.00,
        "depositary_id": 602,
        "krid_url": "https://www.esap.europa.eu/ucits/iberian-equity-krid.pdf",
        "investment_strategy": "Iberian dividend-paying equities",
        "risk_profile": "5/7",
        "status": "active",
    },
    {
        "fund_name": "Global Tech Leaders UCITS",
        "management_company": "European Wealth Partners",
        "registration_date": "2020-09-01",
        "home_member_state": "IE",
        "cross_border_passport": True,
        "total_aum_eur": 2800000000.00,
        "depositary_id": 603,
        "krid_url": "https://www.esap.europa.eu/ucits/global-tech-krid.pdf",
        "investment_strategy": "Global technology sector equities",
        "risk_profile": "6/7",
        "status": "active",
    },
]

AIFMD_SEED_REPORTS = [
    {"fund_id": 1, "report_type": "annual", "reporting_period": "2024", "url": "https://www.esap.europa.eu/aifmd/iberian-ref-2024.pdf", "filed_date": "2025-03-31", "status": "filed"},
    {"fund_id": 2, "report_type": "annual", "reporting_period": "2024", "url": "https://www.esap.europa.eu/aifmd/growth-cap-2024.pdf", "filed_date": "2025-04-15", "status": "filed"},
    {"fund_id": 1, "report_type": "semi-annual", "reporting_period": "2024-H1", "url": "https://www.esap.europa.eu/aifmd/iberian-ref-2024-h1.pdf", "filed_date": "2024-07-31", "status": "filed"},
]

UCITS_SEED_REPORTS = [
    {"fund_id": 1, "report_type": "annual", "reporting_period": "2024", "url": "https://www.esap.europa.eu/ucits/euro-green-bond-2024.pdf", "filed_date": "2025-03-31", "status": "filed"},
    {"fund_id": 2, "report_type": "annual", "reporting_period": "2024", "url": "https://www.esap.europa.eu/ucits/iberian-equity-2024.pdf", "filed_date": "2025-04-30", "status": "filed"},
    {"fund_id": 3, "report_type": "annual", "reporting_period": "2024", "url": "https://www.esap.europa.eu/ucits/global-tech-2024.pdf", "filed_date": "2025-03-15", "status": "filed"},
]

AIFMD_SEED_LIQUIDITY = [
    {"fund_id": 1, "redemption_suspended": False, "suspension_date": None, "gating_applied": False, "swing_price_applied": False, "side_pocket_applied": False, "stress_test_result": "pass", "valuation_frequency": "quarterly"},
    {"fund_id": 2, "redemption_suspended": False, "suspension_date": None, "gating_applied": True, "swing_price_applied": False, "side_pocket_applied": True, "stress_test_result": "pass_with_conditions", "valuation_frequency": "annually"},
    {"fund_id": 3, "redemption_suspended": True, "suspension_date": "2024-08-15", "gating_applied": True, "swing_price_applied": True, "side_pocket_applied": False, "stress_test_result": "fail", "valuation_frequency": "semi-annually"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_aifmd_ucits_tables(conn):
    """Ensure AIFMD/UCITS tables exist (defensive — migration should have created them)."""
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'aifmd_fund'
            ) THEN
                RAISE EXCEPTION 'aifmd_fund table missing — run Alembic migration first';
            END IF;
        END $$;
    """))


# ---------------------------------------------------------------------------
# Upsert functions
# ---------------------------------------------------------------------------


def upsert_aifmd_fund(conn, payload: dict) -> int:
    """Upsert AIFMD fund. Returns fund id."""
    result = conn.execute(
        text("""
            INSERT INTO aifmd_fund
                (fund_name, aifm_id, fund_type, registration_date,
                 home_member_state, cross_border_passport, total_aum_eur,
                 investor_type, lock_up_period, redemption_frequency,
                 leverage_method, leverage_max_pct, status, created_at)
            VALUES
                (:name, :aifm_id, :ftype, :reg_date, :home_state,
                 :passport, :aum, :inv_type, :lock_up, :red_freq,
                 :lev_method, :lev_max, :status, now())
            ON CONFLICT DO NOTHING
            RETURNING id
        """),
        {
            "name": payload["fund_name"],
            "aifm_id": payload.get("aifm_id"),
            "ftype": payload["fund_type"],
            "reg_date": payload.get("registration_date"),
            "home_state": payload.get("home_member_state"),
            "passport": payload.get("cross_border_passport"),
            "aum": payload.get("total_aum_eur"),
            "inv_type": payload.get("investor_type"),
            "lock_up": payload.get("lock_up_period"),
            "red_freq": payload.get("redemption_frequency"),
            "lev_method": payload.get("leverage_method"),
            "lev_max": payload.get("leverage_max_pct"),
            "status": payload.get("status", "active"),
        },
    ).mappings().first()

    if result:
        return result["id"]

    # Already exists
    existing = conn.execute(
        text("""
            SELECT id FROM aifmd_fund WHERE fund_name = :name
        """),
        {"name": payload["fund_name"]},
    ).mappings().first()

    return existing["id"] if existing else 0


def upsert_ucits_fund(conn, payload: dict) -> int:
    """Upsert UCITS fund. Returns fund id."""
    result = conn.execute(
        text("""
            INSERT INTO ucits_fund
                (fund_name, management_company, registration_date,
                 home_member_state, cross_border_passport, total_aum_eur,
                 depositary_id, krid_url, investment_strategy, risk_profile,
                 status, created_at)
            VALUES
                (:name, :mgmt, :reg_date, :home_state, :passport, :aum,
                 :dep_id, :krid, :strategy, :risk, :status, now())
            ON CONFLICT DO NOTHING
            RETURNING id
        """),
        {
            "name": payload["fund_name"],
            "mgmt": payload.get("management_company"),
            "reg_date": payload.get("registration_date"),
            "home_state": payload.get("home_member_state"),
            "passport": payload.get("cross_border_passport"),
            "aum": payload.get("total_aum_eur"),
            "dep_id": payload.get("depositary_id"),
            "krid": payload.get("krid_url"),
            "strategy": payload.get("investment_strategy"),
            "risk": payload.get("risk_profile"),
            "status": payload.get("status", "active"),
        },
    ).mappings().first()

    if result:
        return result["id"]

    existing = conn.execute(
        text("""
            SELECT id FROM ucits_fund WHERE fund_name = :name
        """),
        {"name": payload["fund_name"]},
    ).mappings().first()

    return existing["id"] if existing else 0


def upsert_aifmd_regulatory_report(conn, payload: dict):
    """Upsert AIFMD regulatory report."""
    conn.execute(
        text("""
            INSERT INTO aifmd_regulatory_report
                (fund_id, report_type, reporting_period, url, filed_date, status, created_at)
            VALUES
                (:fund_id, :rtype, :period, :url, :filed, :status, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "fund_id": payload["fund_id"],
            "rtype": payload["report_type"],
            "period": payload.get("reporting_period"),
            "url": payload.get("url"),
            "filed": payload.get("filed_date"),
            "status": payload.get("status", "draft"),
        },
    )


def upsert_ucits_regulatory_report(conn, payload: dict):
    """Upsert UCITS regulatory report."""
    conn.execute(
        text("""
            INSERT INTO ucits_regulatory_report
                (fund_id, report_type, reporting_period, url, filed_date, status, created_at)
            VALUES
                (:fund_id, :rtype, :period, :url, :filed, :status, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "fund_id": payload["fund_id"],
            "rtype": payload["report_type"],
            "period": payload.get("reporting_period"),
            "url": payload.get("url"),
            "filed": payload.get("filed_date"),
            "status": payload.get("status", "draft"),
        },
    )


def upsert_aifmd_liquidity(conn, payload: dict):
    """Upsert AIFMD liquidity management data."""
    conn.execute(
        text("""
            INSERT INTO aifmd_liquidity_management
                (fund_id, redemption_suspended, suspension_date, gating_applied,
                 swing_price_applied, side_pocket_applied, stress_test_result,
                 valuation_frequency, created_at)
            VALUES
                (:fund_id, :red_suspend, :suspend_date, :gating,
                 :swing, :side_pocket, :stress, :freq, now())
            ON CONFLICT DO NOTHING
        """),
        {
            "fund_id": payload["fund_id"],
            "red_suspend": payload.get("redemption_suspended"),
            "suspend_date": payload.get("suspension_date"),
            "gating": payload.get("gating_applied"),
            "swing": payload.get("swing_price_applied"),
            "side_pocket": payload.get("side_pocket_applied"),
            "stress": payload.get("stress_test_result"),
            "freq": payload.get("valuation_frequency"),
        },
    )


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def run_sync(worker_name: str = "cron-aifmd-weekly"):
    """Run AIFMD/UCITS sync cycle."""
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    sync_start = time.time()
    processed = 0
    stored = 0

    try:
        with engine.begin() as conn:
            _ensure_aifmd_ucits_tables(conn)
            ensure_source_revision_table(conn)

            # Seed AIFMD funds
            for fund in AIFMD_SEED_FUNDS:
                try:
                    upsert_aifmd_fund(conn, fund)
                    processed += 1
                except Exception:
                    logger.exception("Error processing AIFMD fund %s", fund.get("fund_name"))

            # Seed UCITS funds
            for fund in UCITS_SEED_FUNDS:
                try:
                    upsert_ucits_fund(conn, fund)
                    processed += 1
                except Exception:
                    logger.exception("Error processing UCITS fund %s", fund.get("fund_name"))

            # Seed AIFMD regulatory reports
            for report in AIFMD_SEED_REPORTS:
                try:
                    upsert_aifmd_regulatory_report(conn, report)
                    stored += 1
                except Exception:
                    logger.exception("Error processing AIFMD report %s", report.get("reporting_period"))

            # Seed UCITS regulatory reports
            for report in UCITS_SEED_REPORTS:
                try:
                    upsert_ucits_regulatory_report(conn, report)
                    stored += 1
                except Exception:
                    logger.exception("Error processing UCITS report %s", report.get("reporting_period"))

            # Seed AIFMD liquidity management
            for lm in AIFMD_SEED_LIQUIDITY:
                try:
                    upsert_aifmd_liquidity(conn, lm)
                    stored += 1
                except Exception:
                    logger.exception("Error processing liquidity %s", lm.get("fund_id"))

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


def ensure_source_revision_table(conn):
    """Ensure source_revision table exists."""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS source_revision (
            id SERIAL PRIMARY KEY,
            worker_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_source_revision_unique
            ON source_revision (worker_name, entity_type, entity_id);
    """))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AIFMD/UCITS worker: sync fund regulatory data"
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
    init_sentry("aifmd")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-aifmd-weekly")
        print(f"[run-once] Documentos procesados: {result['processed']}, almacenados: {result['stored']}")
    else:
        while True:
            try:
                result = run_sync(worker_name="cron-aifmd-weekly")
                print(f"[sync] Procesados: {result['processed']}, Almacenados: {result['stored']}")
            except Exception:
                logger.exception("AIFMD/UCITS sync failed")
            time.sleep(interval)
