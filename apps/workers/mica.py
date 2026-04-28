"""Worker para ingestion de datos MiCA / crypto-asset.

Fase 31 — Expansion regulatoria.

Ingesta datos de proveedores de servicios de criptoactivos (CASP),
criptoactivos bajo MiCA (Reglamento 2023/1114), activos tokenizados,
wallets custodias y transacciones para DAC8/DAC9.

No depende de un endpoint unico — usa datos estructurados de fuentes
oficiales UE/ES y datos de referencia del ecosistema cripto.
"""

import argparse
import json
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
# Seed data — CASP (Crypto-Asset Service Providers)
# ---------------------------------------------------------------------------
# Fuentes: ESMA public register, national competent authorities (CNMV, BaFin,
# AMF, AFM), ESRB warnings. Valores de ejemplo para poblacion inicial.

SEED_CASPS = [
    {
        "name": "Bitso",
        "registration_number": "ES-CASP-2024-001",
        "home_member_state": "Mexico/ES",
        "passport_active": True,
        "services_offered": {"exchange": True, "custody": True, "transfer": False},
        "status": "active",
    },
    {
        "name": "Bit2Me",
        "registration_number": "ES-CASP-2024-002",
        "home_member_state": "Spain",
        "passport_active": True,
        "services_offered": {"exchange": True, "custody": True, "transfer": True},
        "status": "active",
    },
    {
        "name": "Coinbase Europe Ltd",
        "registration_number": "IE-CASP-2024-001",
        "home_member_state": "Ireland",
        "passport_active": True,
        "services_offered": {"exchange": True, "custody": False, "transfer": True},
        "status": "active",
    },
    {
        "name": "Bitstamp",
        "registration_number": "LT-CASP-2024-001",
        "home_member_state": "Lithuania",
        "passport_active": True,
        "services_offered": {"exchange": True, "custody": True, "transfer": True},
        "status": "active",
    },
    {
        "name": "Kraken Services",
        "registration_number": "DE-CASP-2024-001",
        "home_member_state": "Germany",
        "passport_active": True,
        "services_offered": {"exchange": True, "custody": True, "transfer": False},
        "status": "active",
    },
]

# ---------------------------------------------------------------------------
# Seed data — Crypto Assets (MiCA classification)
# ---------------------------------------------------------------------------
# Clasificacion MiCA: e-money tokens, asset-referenced tokens, utility tokens,
# otros criptoactivos. Datos de referencia de activos principales.

SEED_CRYPTO_ASSETS = [
    {
        "asset_type": "utility_token",
        "reference_uid": "ETH-ethereum",
        "issuer_jurisdiction": "Switzerland/Decentralized",
        "is_sha": False,
        "market_value_eur": 2800000000000,
        "holders_count": 240000000,
        "status": "active",
    },
    {
        "asset_type": "utility_token",
        "reference_uid": "BTC-bitcoin",
        "issuer_jurisdiction": "Decentralized",
        "is_sha": False,
        "market_value_eur": 1600000000000,
        "holders_count": 590000000,
        "status": "active",
    },
    {
        "asset_type": "e-money_token",
        "reference_uid": "USDC-circle",
        "issuer_jurisdiction": "United States",
        "is_sha": True,
        "market_value_eur": 42000000000,
        "holders_count": 120000000,
        "status": "active",
    },
    {
        "asset_type": "e-money_token",
        "reference_uid": "USDT-tether",
        "issuer_jurisdiction": "British Virgin Islands",
        "is_sha": True,
        "market_value_eur": 138000000000,
        "holders_count": 150000000,
        "status": "active",
    },
    {
        "asset_type": "asset_referenced_token",
        "reference_uid": "DAI-maker",
        "issuer_jurisdiction": "Decentralized",
        "is_sha": False,
        "market_value_eur": 5300000000,
        "holders_count": 500000,
        "status": "active",
    },
    {
        "asset_type": "other",
        "reference_uid": "SOL-solana",
        "issuer_jurisdiction": "Switzerland/Decentralized",
        "is_sha": False,
        "market_value_eur": 85000000000,
        "holders_count": 20000000,
        "status": "active",
    },
]

# ---------------------------------------------------------------------------
# Seed data — Tokenized Assets
# ---------------------------------------------------------------------------

SEED_TOKENIZED_ASSETS = [
    {
        "underlying_type": "equity",
        "face_value": 100.00,
        "total_amount": 1000000,
        "listing_date": "2025-03-15",
        "regulated_market": "Euronext",
        "status": "active",
    },
    {
        "underlying_type": "real_estate",
        "face_value": 500.00,
        "total_amount": 500000,
        "listing_date": "2025-06-01",
        "regulated_market": "Nasdaq Copenhagen",
        "status": "active",
    },
    {
        "underlying_type": "government_bond",
        "face_value": 1000.00,
        "total_amount": 5000000,
        "listing_date": "2025-01-10",
        "regulated_market": "Deutsche Boerse",
        "status": "active",
    },
]

# ---------------------------------------------------------------------------
# Seed data — Wallet Custodians
# ---------------------------------------------------------------------------

SEED_WALLET_CUSTODIANS = [
    {
        "entity_id": 1,
        "wallet_type": "cold",
        "custody_mechanism": "multi-signature",
        "insurance_coverage": 100000000,
        "audit_frequency": "quarterly",
        "status": "active",
    },
    {
        "entity_id": 2,
        "wallet_type": "hybrid",
        "custody_mechanism": "HSM",
        "insurance_coverage": 50000000,
        "audit_frequency": "monthly",
        "status": "active",
    },
    {
        "entity_id": 3,
        "wallet_type": "hot",
        "custody_mechanism": "software",
        "insurance_coverage": 10000000,
        "audit_frequency": "quarterly",
        "status": "active",
    },
]

# ---------------------------------------------------------------------------
# Seed data — Crypto Transactions (DAC8/DAC9 reporting)
# ---------------------------------------------------------------------------
# Datos de ejemplo para demostracion del esquema de reporte.
# En produccion, estos se poblan desde proveedores de servicios CASP.

SEED_CRYPTO_TRANSACTIONS = [
    {
        "sender_wallet": "0x1234...abcd",
        "receiver_wallet": "0x5678...efgh",
        "sender_jurisdiction": "Spain",
        "receiver_jurisdiction": "France",
        "asset_type": "e-money_token",
        "amount": 5000.00,
        "value_eur": 5000.00,
        "timestamp": "2025-06-15T10:30:00Z",
        "reporting_period": "2025-02",
    },
    {
        "sender_wallet": "bc1q...xy12",
        "receiver_wallet": "bc1q...ab34",
        "sender_jurisdiction": "Germany",
        "receiver_jurisdiction": "Italy",
        "asset_type": "utility_token",
        "amount": 1.500000000000000000,
        "value_eur": 4200.00,
        "timestamp": "2025-07-20T14:45:00Z",
        "reporting_period": "2025-03",
    },
    {
        "sender_wallet": "0xabcd...1234",
        "receiver_wallet": "0x5678...9012",
        "sender_jurisdiction": "Netherlands",
        "receiver_jurisdiction": "Spain",
        "asset_type": "asset_referenced_token",
        "amount": 10000.00,
        "value_eur": 9980.00,
        "timestamp": "2025-08-05T09:00:00Z",
        "reporting_period": "2025-03",
    },
]

# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------


def upsert_casp(conn, data: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO casp (name, registration_number, home_member_state,
                              passport_active, services_offered, status)
            VALUES (:name, :registration_number, :home_member_state,
                    :passport_active, :services_offered, :status)
            ON CONFLICT (registration_number) DO UPDATE SET
                name = EXCLUDED.name,
                home_member_state = EXCLUDED.home_member_state,
                passport_active = EXCLUDED.passport_active,
                services_offered = EXCLUDED.services_offered,
                status = EXCLUDED.status
            """
        ),
        {
            "name": data["name"],
            "registration_number": data.get("registration_number"),
            "home_member_state": data.get("home_member_state"),
            "passport_active": data.get("passport_active", False),
            "services_offered": json.dumps(data.get("services_offered")) if data.get("services_offered") else None,
            "status": data.get("status", "active"),
        },
    )


def upsert_crypto_asset(conn, data: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction,
                                      is_sha, market_value_eur, holders_count, status)
            VALUES (:asset_type, :reference_uid, :issuer_jurisdiction,
                    :is_sha, :market_value_eur, :holders_count, :status)
            ON CONFLICT (reference_uid) DO UPDATE SET
                asset_type = EXCLUDED.asset_type,
                issuer_jurisdiction = EXCLUDED.issuer_jurisdiction,
                is_sha = EXCLUDED.is_sha,
                market_value_eur = EXCLUDED.market_value_eur,
                holders_count = EXCLUDED.holders_count,
                status = EXCLUDED.status
            """
        ),
        {
            "asset_type": data["asset_type"],
            "reference_uid": data.get("reference_uid"),
            "issuer_jurisdiction": data.get("issuer_jurisdiction"),
            "is_sha": data.get("is_sha", False),
            "market_value_eur": data.get("market_value_eur"),
            "holders_count": data.get("holders_count"),
            "status": data.get("status", "active"),
        },
    )


def upsert_tokenized_asset(conn, data: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO tokenized_asset (underlying_type, face_value, total_amount,
                                         listing_date, regulated_market, status)
            VALUES (:underlying_type, :face_value, :total_amount,
                    :listing_date, :regulated_market, :status)
            ON CONFLICT (id) DO UPDATE SET
                underlying_type = EXCLUDED.underlying_type,
                face_value = EXCLUDED.face_value,
                total_amount = EXCLUDED.total_amount,
                listing_date = EXCLUDED.listing_date,
                regulated_market = EXCLUDED.regulated_market,
                status = EXCLUDED.status
            """
        ),
        {
            "underlying_type": data.get("underlying_type"),
            "face_value": data.get("face_value"),
            "total_amount": data.get("total_amount"),
            "listing_date": data.get("listing_date"),
            "regulated_market": data.get("regulated_market"),
            "status": data.get("status", "active"),
        },
    )


def upsert_wallet_custodian(conn, data: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO wallet_custodian (entity_id, wallet_type, custody_mechanism,
                                          insurance_coverage, audit_frequency, status)
            VALUES (:entity_id, :wallet_type, :custody_mechanism,
                    :insurance_coverage, :audit_frequency, :status)
            ON CONFLICT(entity_id) DO UPDATE SET
                wallet_type = EXCLUDED.wallet_type,
                custody_mechanism = EXCLUDED.custody_mechanism,
                insurance_coverage = EXCLUDED.insurance_coverage,
                audit_frequency = EXCLUDED.audit_frequency,
                status = EXCLUDED.status
            """
        ),
        {
            "entity_id": data.get("entity_id"),
            "wallet_type": data.get("wallet_type"),
            "custody_mechanism": data.get("custody_mechanism"),
            "insurance_coverage": data.get("insurance_coverage"),
            "audit_frequency": data.get("audit_frequency"),
            "status": data.get("status", "active"),
        },
    )


def upsert_crypto_transaction(conn, data: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO crypto_transaction (sender_wallet, receiver_wallet,
                                            sender_jurisdiction, receiver_jurisdiction,
                                            asset_type, amount, value_eur,
                                            timestamp, reporting_period)
            VALUES (:sender_wallet, :receiver_wallet, :sender_jurisdiction,
                    :receiver_jurisdiction, :asset_type, :amount, :value_eur,
                    :timestamp, :reporting_period)
            ON CONFLICT(sender_wallet, receiver_wallet, timestamp, reporting_period) DO UPDATE SET
                sender_jurisdiction = EXCLUDED.sender_jurisdiction,
                receiver_jurisdiction = EXCLUDED.receiver_jurisdiction,
                asset_type = EXCLUDED.asset_type,
                amount = EXCLUDED.amount,
                value_eur = EXCLUDED.value_eur
            """
        ),
        {
            "sender_wallet": data.get("sender_wallet"),
            "receiver_wallet": data.get("receiver_wallet"),
            "sender_jurisdiction": data.get("sender_jurisdiction"),
            "receiver_jurisdiction": data.get("receiver_jurisdiction"),
            "asset_type": data.get("asset_type"),
            "amount": data.get("amount"),
            "value_eur": data.get("value_eur"),
            "timestamp": data.get("timestamp"),
            "reporting_period": data.get("reporting_period"),
        },
    )


# ---------------------------------------------------------------------------
# Main sync
# ---------------------------------------------------------------------------


def run_sync(
    worker_name: str = "worker-mica",
) -> dict[str, int]:
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()

    try:
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)

            casps_stored = 0
            for data in SEED_CASPS:
                upsert_casp(conn, data)
                casps_stored += 1

            assets_stored = 0
            for data in SEED_CRYPTO_ASSETS:
                upsert_crypto_asset(conn, data)
                assets_stored += 1

            tokenized_stored = 0
            for data in SEED_TOKENIZED_ASSETS:
                upsert_tokenized_asset(conn, data)
                tokenized_stored += 1

            custodians_stored = 0
            for data in SEED_WALLET_CUSTODIANS:
                upsert_wallet_custodian(conn, data)
                custodians_stored += 1

            transactions_stored = 0
            for data in SEED_CRYPTO_TRANSACTIONS:
                upsert_crypto_transaction(conn, data)
                transactions_stored += 1

            total_rows = casps_stored + assets_stored + tokenized_stored + custodians_stored + transactions_stored
            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=total_rows,
                documentos_upserted=total_rows,
                started_at=sync_start,
            )

        return {
            "casps": casps_stored,
            "crypto_assets": assets_stored,
            "tokenized_assets": tokenized_stored,
            "wallet_custodians": custodians_stored,
            "crypto_transactions": transactions_stored,
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
        description="MiCA/crypto worker: sync MiCA crypto-asset data model"
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
    init_sentry("mica")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-mica-weekly")
        print(
            f"[run-once] CASPs: {result['casps']}, "
            f"Crypto assets: {result['crypto_assets']}, "
            f"Tokenized: {result['tokenized_assets']}, "
            f"Custodians: {result['wallet_custodians']}, "
            f"Transactions: {result['crypto_transactions']}"
        )
    else:
        print(f"Starting MiCA worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced casps={result['casps']}, assets={result['crypto_assets']}, "
                f"tokenized={result['tokenized_assets']}, custodians={result['wallet_custodians']}, "
                f"txs={result['crypto_transactions']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
