#!/usr/bin/env python3
"""Seed de datos MiCA (Reglamento UE 2023/1114) y crypto-asset services.

Inyecta datos curados de CASP registrados en Espana y ejemplos
de criptoactivos, activos tokenizados, custodios y transacciones.

Uso:
    python scripts/data/seed_mica.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_rows

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"


CASP_DATA = [
    {
        "name": "Bit2Me S.L.",
        "registration_number": "ES-CASP-2024-001",
        "home_member_state": "ES",
        "passport_active": False,
        "services_offered": ["exchange", "payment"],
        "status": "active",
    },
    {
        "name": "Coinbase Europe Ltd. (sucursal Espana)",
        "registration_number": "ES-CASP-2024-002",
        "home_member_state": "IE",
        "passport_active": True,
        "services_offered": ["exchange", "custody", "execution"],
        "status": "active",
    },
    {
        "name": "Bitso Espana S.L.U.",
        "registration_number": "ES-CASP-2024-003",
        "home_member_state": "ES",
        "passport_active": False,
        "services_offered": ["exchange", "custody"],
        "status": "active",
    },
    {
        "name": "Kraken Europe Ltd. (sucursal Espana)",
        "registration_number": "ES-CASP-2024-004",
        "home_member_state": "MT",
        "passport_active": True,
        "services_offered": ["exchange", "execution", "payment"],
        "status": "active",
    },
    {
        "name": "Bitstamp Europe Ltd. (sucursal Espana)",
        "registration_number": "ES-CASP-2024-005",
        "home_member_state": "LT",
        "passport_active": True,
        "services_offered": ["exchange", "payment"],
        "status": "active",
    },
    {
        "name": "Binance Europe Services Ltd.",
        "registration_number": "ES-CASP-2024-006",
        "home_member_state": "IE",
        "passport_active": True,
        "services_offered": ["exchange", "custody", "execution", "payment"],
        "status": "active",
    },
    {
        "name": "Crypto.com Europe DAC (sucursal Espana)",
        "registration_number": "ES-CASP-2024-007",
        "home_member_state": "IE",
        "passport_active": True,
        "services_offered": ["exchange", "custody", "payment"],
        "status": "active",
    },
    {
        "name": "Revolut Ltd. (sucursal Espana) — Crypto",
        "registration_number": "ES-CASP-2024-008",
        "home_member_state": "LT",
        "passport_active": True,
        "services_offered": ["exchange", "payment"],
        "status": "active",
    },
    {
        "name": "Nunetex S.L.",
        "registration_number": "ES-CASP-2024-009",
        "home_member_state": "ES",
        "passport_active": False,
        "services_offered": ["exchange", "execution"],
        "status": "active",
    },
    {
        "name": "Paxful Espana S.L.",
        "registration_number": "ES-CASP-2024-010",
        "home_member_state": "ES",
        "passport_active": False,
        "services_offered": ["exchange"],
        "status": "active",
    },
]


CRYPTO_ASSETS = [
    {
        "asset_type": "utility",
        "reference_uid": "UNI-Ethereum",
        "issuer_jurisdiction": "US",
        "is_sha": False,
        "market_value_eur": 8500000000.00,
        "holders_count": 520000,
        "status": "active",
    },
    {
        "asset_type": "utility",
        "reference_uid": "LINK-Ethereum",
        "issuer_jurisdiction": "US",
        "is_sha": False,
        "market_value_eur": 12000000000.00,
        "holders_count": 890000,
        "status": "active",
    },
    {
        "asset_type": "asset-referenced",
        "reference_uid": "USDC-Ethereum",
        "issuer_jurisdiction": "US",
        "is_sha": True,
        "market_value_eur": 42000000000.00,
        "holders_count": 2100000,
        "status": "active",
    },
    {
        "asset_type": "e-money",
        "reference_uid": "EURC-Ethereum",
        "issuer_jurisdiction": "IE",
        "is_sha": True,
        "market_value_eur": 180000000.00,
        "holders_count": 45000,
        "status": "active",
    },
]


TOKENIZED_ASSETS = [
    {
        "underlying_type": "bond",
        "issuer_id": None,
        "face_value": 1000.00,
        "total_amount": 50000000.00,
        "listing_date": "2025-06-15",
        "regulated_market": "BME",
        "status": "active",
    },
    {
        "underlying_type": "equity",
        "issuer_id": None,
        "face_value": 10.00,
        "total_amount": 10000000.00,
        "listing_date": "2025-09-01",
        "regulated_market": "Euronext Madrid",
        "status": "active",
    },
    {
        "underlying_type": "real-estate",
        "issuer_id": None,
        "face_value": 500.00,
        "total_amount": 5000000.00,
        "listing_date": "2025-11-20",
        "regulated_market": "Propy EU",
        "status": "active",
    },
]


WALLET_CUSTODIANS = [
    {
        "entity_id": None,
        "wallet_type": "cold",
        "custody_mechanism": "multi-sig",
        "insurance_coverage": 250000000.00,
        "audit_frequency": "quarterly",
        "status": "active",
    },
    {
        "entity_id": None,
        "wallet_type": "hybrid",
        "custody_mechanism": "MPC",
        "insurance_coverage": 150000000.00,
        "audit_frequency": "monthly",
        "status": "active",
    },
    {
        "entity_id": None,
        "wallet_type": "hot",
        "custody_mechanism": "hardware",
        "insurance_coverage": 50000000.00,
        "audit_frequency": "monthly",
        "status": "active",
    },
]


CRYPTO_TRANSACTIONS = [
    {
        "sender_wallet": "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a00",
        "receiver_wallet": "0x9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f00",
        "sender_jurisdiction": "ES",
        "receiver_jurisdiction": "DE",
        "asset_type": "utility",
        "amount": 1500.00,
        "value_eur": 12750.00,
        "timestamp": "2025-10-15 14:30:00+00",
        "reporting_period": "2025-10",
        "status": "reported",
    },
    {
        "sender_wallet": "0x2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b11",
        "receiver_wallet": "0x8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e22",
        "sender_jurisdiction": "FR",
        "receiver_jurisdiction": "ES",
        "asset_type": "asset-referenced",
        "amount": 50000.00,
        "value_eur": 50000.00,
        "timestamp": "2025-11-02 09:15:00+00",
        "reporting_period": "2025-11",
        "status": "reported",
    },
    {
        "sender_wallet": "0x3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c23",
        "receiver_wallet": "0x7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e2d33",
        "sender_jurisdiction": "ES",
        "receiver_jurisdiction": "PT",
        "asset_type": "e-money",
        "amount": 25000.00,
        "value_eur": 25000.00,
        "timestamp": "2025-12-01 16:45:00+00",
        "reporting_period": "2025-12",
        "status": "reported",
    },
]


def seed_casp(db, dry_run: bool) -> int:
    """Insertar CASP curados."""
    count = 0
    for casp in CASP_DATA:
        if dry_run:
            print(f"[DRY-RUN] INSERT casp: {casp['name']} ({casp['registration_number']})")
            count += 1
            continue

        existing = db.execute(
            "SELECT id FROM casp WHERE registration_number = %s AND home_member_state = %s",
            (casp["registration_number"], casp["home_member_state"]),
        ).fetchone()

        if existing:
            print(f"SKIP casp already exists: {casp['name']}")
            continue

        db.execute(
            """INSERT INTO casp (name, registration_number, home_member_state,
                                passport_active, services_offered, status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                casp["name"],
                casp["registration_number"],
                casp["home_member_state"],
                casp["passport_active"],
                casp["services_offered"],
                casp["status"],
            ),
        )
        count += 1
        print(f"SEED casp: {casp['name']} ({casp['registration_number']})")

    return count


def seed_crypto_assets(db, dry_run: bool) -> int:
    """Insertar criptoactivos curados."""
    count = 0
    for asset in CRYPTO_ASSETS:
        if dry_run:
            print(f"[DRY-RUN] INSERT crypto_asset: {asset['reference_uid']} ({asset['asset_type']})")
            count += 1
            continue

        existing = db.execute(
            "SELECT id FROM crypto_asset WHERE reference_uid = %s",
            (asset["reference_uid"],),
        ).fetchone()

        if existing:
            print(f"SKIP crypto_asset already exists: {asset['reference_uid']}")
            continue

        db.execute(
            """INSERT INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction,
                                         is_sha, market_value_eur, holders_count, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                asset["asset_type"],
                asset["reference_uid"],
                asset["issuer_jurisdiction"],
                asset["is_sha"],
                asset["market_value_eur"],
                asset["holders_count"],
                asset["status"],
            ),
        )
        count += 1
        print(f"SEED crypto_asset: {asset['reference_uid']}")

    return count


def seed_tokenized_assets(db, dry_run: bool) -> int:
    """Insertar activos tokenizados curados."""
    count = 0
    for asset in TOKENIZED_ASSETS:
        if dry_run:
            print(f"[DRY-RUN] INSERT tokenized_asset: {asset['underlying_type']} ({asset['regulated_market']})")
            count += 1
            continue

        db.execute(
            """INSERT INTO tokenized_asset (underlying_type, issuer_id, face_value,
                                            total_amount, listing_date, regulated_market, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                asset["underlying_type"],
                asset["issuer_id"],
                asset["face_value"],
                asset["total_amount"],
                asset["listing_date"],
                asset["regulated_market"],
                asset["status"],
            ),
        )
        count += 1
        print(f"SEED tokenized_asset: {asset['underlying_type']} ({asset['regulated_market']})")

    return count


def seed_wallet_custodians(db, dry_run: bool) -> int:
    """Insertar custodios de wallets curados."""
    count = 0
    for cust in WALLET_CUSTODIANS:
        if dry_run:
            print(f"[DRY-RUN] INSERT wallet_custodian: {cust['wallet_type']} ({cust['custody_mechanism']})")
            count += 1
            continue

        db.execute(
            """INSERT INTO wallet_custodian (entity_id, wallet_type, custody_mechanism,
                                             insurance_coverage, audit_frequency, status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                cust["entity_id"],
                cust["wallet_type"],
                cust["custody_mechanism"],
                cust["insurance_coverage"],
                cust["audit_frequency"],
                cust["status"],
            ),
        )
        count += 1
        print(f"SEED wallet_custodian: {cust['wallet_type']} ({cust['custody_mechanism']})")

    return count


def seed_crypto_transactions(db, dry_run: bool) -> int:
    """Insertar transacciones crypto curadas."""
    count = 0
    for txn in CRYPTO_TRANSACTIONS:
        if dry_run:
            print(f"[DRY-RUN] INSERT crypto_transaction: {txn['asset_type']} ({txn['reporting_period']})")
            count += 1
            continue

        db.execute(
            """INSERT INTO crypto_transaction (sender_wallet, receiver_wallet,
                                               sender_jurisdiction, receiver_jurisdiction,
                                               asset_type, amount, value_eur, timestamp,
                                               reporting_period, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                txn["sender_wallet"],
                txn["receiver_wallet"],
                txn["sender_jurisdiction"],
                txn["receiver_jurisdiction"],
                txn["asset_type"],
                txn["amount"],
                txn["value_eur"],
                txn["timestamp"],
                txn["reporting_period"],
                txn["status"],
            ),
        )
        count += 1
        print(f"SEED crypto_transaction: {txn['asset_type']} ({txn['reporting_period']})")

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed MiCA/Crypto data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database URL")
    args = parser.parse_args()

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"=== MiCA/Crypto Seed [{mode}] ===")

    conn = psycopg.connect(args.database_url, row_factory=dict_rows)
    try:
        cur = conn.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'casp')")
        if not cur.fetchone()["exists"]:
            print("ERROR: tabla 'casp' no existe. Ejecuta 'alembic upgrade head' primero.")
            sys.exit(1)

        total = 0
        total += seed_casp(conn, args.dry_run)
        total += seed_crypto_assets(conn, args.dry_run)
        total += seed_tokenized_assets(conn, args.dry_run)
        total += seed_wallet_custodians(conn, args.dry_run)
        total += seed_crypto_transactions(conn, args.dry_run)

        if not args.dry_run:
            conn.commit()

        print(f"\nTotal rows seeded: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
