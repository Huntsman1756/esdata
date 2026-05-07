"""Worker para ingestion de datos DAC8/DAC9.

Fase 31 — Expansion regulatoria.

Ingesta entidades de reporte DAC8/DAC9, reportes periodicos de
criptoactivos y titulares de wallet conforme a las directivas
de intercambio automatico de informacion de la UE.

DAC8 (Directiva 2023/2819): reporte de informacion sobre criptoactivos.
DAC9 (Directiva 2021/2101): ampliacion del intercambio automatico.
"""

import argparse
import time
from datetime import UTC, datetime

from boe import _ensure_sync_log_table, log_sync
from runtime import get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# ---------------------------------------------------------------------------
# Seed data — DAC Reporting Entities
# ---------------------------------------------------------------------------
# Entidades obligadas a reportar bajo DAC8/DAC9: CASP registrados
# en la UE, exchanges de cripto-fiat y custodians de wallets.

SEED_DAC_REPORTING_ENTITIES = [
    {
        "tin": "ES-CASP-2024-001",
        "entity_type": "crypto-asset service provider",
        "member_state": "Spain",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
    },
    {
        "tin": "DE-CASP-2024-002",
        "entity_type": "crypto-asset service provider",
        "member_state": "Germany",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
    },
    {
        "tin": "FR-EXCHANGE-2024-003",
        "entity_type": "exchange",
        "member_state": "France",
        "dac8_registered": True,
        "dac9_registered": False,
        "status": "active",
    },
    {
        "tin": "NL-CUST-2024-004",
        "entity_type": "custodian",
        "member_state": "Netherlands",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
    },
    {
        "tin": "IT-CASP-2024-005",
        "entity_type": "crypto-asset service provider",
        "member_state": "Italy",
        "dac8_registered": False,
        "dac9_registered": False,
        "status": "pending",
    },
]

# ---------------------------------------------------------------------------
# Seed data — DAC Crypto Reports
# ---------------------------------------------------------------------------
# Reportes periodicos de transacciones cripto.

SEED_DAC_CRYPTO_REPORTS = [
    {
        "entity_id": 1,
        "reporting_period": "2025-Q1",
        "submitted_at": "2025-04-15T10:00:00Z",
        "status": "submitted",
        "crypto_transactions_count": 15234,
        "wallet_holders_count": 8432,
    },
    {
        "entity_id": 2,
        "reporting_period": "2025-Q1",
        "submitted_at": "2025-04-20T14:30:00Z",
        "status": "submitted",
        "crypto_transactions_count": 28901,
        "wallet_holders_count": 15678,
    },
    {
        "entity_id": 3,
        "reporting_period": "2025-Q1",
        "submitted_at": None,
        "status": "draft",
        "crypto_transactions_count": 5420,
        "wallet_holders_count": 3210,
    },
]

# ---------------------------------------------------------------------------
# Seed data — DAC Wallet Holders
# ---------------------------------------------------------------------------
# Titulares de wallet dentro de reportes DAC8/DAC9.

SEED_DAC_WALLET_HOLDERS = [
    {
        "report_id": 1,
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "holder_tin": "ES12345678Z",
        "holder_member_state": "Spain",
        "holder_type": "individual",
        "total_value_eur": 45000.50,
        "verification_status": "verified",
    },
    {
        "report_id": 1,
        "wallet_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        "holder_tin": "DE98765432A",
        "holder_member_state": "Germany",
        "holder_type": "entity",
        "total_value_eur": 230000.00,
        "verification_status": "verified",
    },
    {
        "report_id": 2,
        "wallet_address": "0xabcdef1234567890abcdef1234567890abcdef12",
        "holder_tin": "FR55556666777",
        "holder_member_state": "France",
        "holder_type": "individual",
        "total_value_eur": 12500.75,
        "verification_status": "pending",
    },
]

# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------


def upsert_dac_reporting_entity(conn, data: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO dac_reporting_entity (tin, entity_type, member_state,
                                              dac8_registered, dac9_registered, status)
            VALUES (:tin, :entity_type, :member_state,
                    :dac8_registered, :dac9_registered, :status)
            ON CONFLICT (tin) DO UPDATE SET
                entity_type = EXCLUDED.entity_type,
                member_state = EXCLUDED.member_state,
                dac8_registered = EXCLUDED.dac8_registered,
                dac9_registered = EXCLUDED.dac9_registered,
                status = EXCLUDED.status
            """
        ),
        {
            "tin": data.get("tin"),
            "entity_type": data.get("entity_type"),
            "member_state": data.get("member_state"),
            "dac8_registered": data.get("dac8_registered", False),
            "dac9_registered": data.get("dac9_registered", False),
            "status": data.get("status", "active"),
        },
    )


def upsert_dac_crypto_report(conn, data: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO dac_crypto_report (entity_id, reporting_period, submitted_at,
                                           status, crypto_transactions_count, wallet_holders_count)
            VALUES (:entity_id, :reporting_period, :submitted_at,
                    :status, :crypto_transactions_count, :wallet_holders_count)
            ON CONFLICT (id) DO UPDATE SET
                entity_id = EXCLUDED.entity_id,
                reporting_period = EXCLUDED.reporting_period,
                submitted_at = EXCLUDED.submitted_at,
                status = EXCLUDED.status,
                crypto_transactions_count = EXCLUDED.crypto_transactions_count,
                wallet_holders_count = EXCLUDED.wallet_holders_count
            """
        ),
        {
            "entity_id": data.get("entity_id"),
            "reporting_period": data.get("reporting_period"),
            "submitted_at": data.get("submitted_at"),
            "status": data.get("status", "draft"),
            "crypto_transactions_count": data.get("crypto_transactions_count", 0),
            "wallet_holders_count": data.get("wallet_holders_count", 0),
        },
    )


def upsert_dac_wallet_holder(conn, data: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO dac_wallet_holder (report_id, wallet_address, holder_tin,
                                           holder_member_state, holder_type,
                                           total_value_eur, verification_status)
            VALUES (:report_id, :wallet_address, :holder_tin,
                    :holder_member_state, :holder_type,
                    :total_value_eur, :verification_status)
            ON CONFLICT (id) DO UPDATE SET
                report_id = EXCLUDED.report_id,
                wallet_address = EXCLUDED.wallet_address,
                holder_tin = EXCLUDED.holder_tin,
                holder_member_state = EXCLUDED.holder_member_state,
                holder_type = EXCLUDED.holder_type,
                total_value_eur = EXCLUDED.total_value_eur,
                verification_status = EXCLUDED.verification_status
            """
        ),
        {
            "report_id": data.get("report_id"),
            "wallet_address": data.get("wallet_address"),
            "holder_tin": data.get("holder_tin"),
            "holder_member_state": data.get("holder_member_state"),
            "holder_type": data.get("holder_type"),
            "total_value_eur": data.get("total_value_eur"),
            "verification_status": data.get("verification_status"),
        },
    )


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def run_sync(worker_name: str = "cron-dac8-dac9-weekly") -> dict:
    """Sync DAC8/DAC9 seed data into the database."""
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()

    total_rows = 0
    entities_stored = 0
    reports_stored = 0
    holders_stored = 0

    try:
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)

            # DAC Reporting Entities
            for data in SEED_DAC_REPORTING_ENTITIES:
                upsert_dac_reporting_entity(conn, data)
                total_rows += 1
                entities_stored += 1

            # DAC Crypto Reports
            for data in SEED_DAC_CRYPTO_REPORTS:
                upsert_dac_crypto_report(conn, data)
                total_rows += 1
                reports_stored += 1

            # DAC Wallet Holders
            for data in SEED_DAC_WALLET_HOLDERS:
                upsert_dac_wallet_holder(conn, data)
                total_rows += 1
                holders_stored += 1

            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=total_rows,
                documentos_upserted=total_rows,
                started_at=sync_start,
            )

        return {
            "reporting_entities": entities_stored,
            "crypto_reports": reports_stored,
            "wallet_holders": holders_stored,
        }
    except Exception as exc:
        entity_id = "dac8"
        if not handle_worker_failure(engine, "dac8", entity_id, "sync_entity", exc):
            logger.warning("Entity dac8 moved to dead-letter")
            return {"reporting_entities": 0, "crypto_reports": 0, "wallet_holders": 0}
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
        description="DAC8/DAC9 worker: sync DAC8/DAC9 crypto-reporting data"
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
    init_sentry("dac8_dac9")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-dac8-dac9-weekly")
        print(
            f"[run-once] Reporting entities: {result['reporting_entities']}, "
            f"Crypto reports: {result['crypto_reports']}, "
            f"Wallet holders: {result['wallet_holders']}"
        )
    else:
        print(f"Starting DAC8/DAC9 worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced entities={result['reporting_entities']}, "
                f"reports={result['crypto_reports']}, "
                f"holders={result['wallet_holders']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
