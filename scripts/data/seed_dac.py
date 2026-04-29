#!/usr/bin/env python3
"""Seed DAC8/DAC9 — Reporting entities, crypto reports y wallet holders.

Crea reportes DAC8/DAC9 de ejemplo para intercambio automatico de informacion.

Uso:
    python scripts/data/seed_dac.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"


ENTITY_DATA = [
    {
        "tin": "ESA12345678",
        "entity_type": "crypto-asset-service-provider",
        "member_state": "ES",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
    },
    {
        "tin": "DEU87654321",
        "entity_type": "crypto-asset-service-provider",
        "member_state": "DE",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
    },
    {
        "tin": "FRA11223344",
        "entity_type": "crypto-wallet-provider",
        "member_state": "FR",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
    },
    {
        "tin": "ITA55667788",
        "entity_type": "crypto-asset-service-provider",
        "member_state": "IT",
        "dac8_registered": False,
        "dac9_registered": True,
        "status": "pending",
    },
]


REPORTS_DATA = [
    {
        "entity_id": None,
        "reporting_period": "2025-Q1",
        "submitted_at": "2025-04-15 10:30:00+00",
        "status": "submitted",
        "crypto_transactions_count": 1250,
        "wallet_holders_count": 487,
    },
    {
        "entity_id": None,
        "reporting_period": "2025-Q2",
        "submitted_at": "2025-07-15 14:00:00+00",
        "status": "submitted",
        "crypto_transactions_count": 1430,
        "wallet_holders_count": 523,
    },
    {
        "entity_id": None,
        "reporting_period": "2025-Q3",
        "submitted_at": "2025-10-15 09:00:00+00",
        "status": "submitted",
        "crypto_transactions_count": 1680,
        "wallet_holders_count": 612,
    },
    {
        "entity_id": None,
        "reporting_period": "2025-Q4",
        "submitted_at": None,
        "status": "draft",
        "crypto_transactions_count": 1890,
        "wallet_holders_count": 698,
    },
]


WALLET_HOLDER_DATA = [
    {"wallet_address": "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a00", "holder_tin": "ESA11223344", "holder_member_state": "ES", "holder_type": "individual", "total_value_eur": 45000.00, "verification_status": "verified"},
    {"wallet_address": "0x2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b11", "holder_tin": "ESA55667788", "holder_member_state": "ES", "holder_type": "individual", "total_value_eur": 128000.00, "verification_status": "verified"},
    {"wallet_address": "0x3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c22", "holder_tin": "DEU99887766", "holder_member_state": "DE", "holder_type": "individual", "total_value_eur": 67500.00, "verification_status": "verified"},
    {"wallet_address": "0x4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d33", "holder_tin": "FRA22334455", "holder_member_state": "FR", "holder_type": "business", "total_value_eur": 234000.00, "verification_status": "verified"},
    {"wallet_address": "0x5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e44", "holder_tin": "ITA66778899", "holder_member_state": "IT", "holder_type": "individual", "total_value_eur": 8900.00, "verification_status": "pending"},
    {"wallet_address": "0x6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f55", "holder_tin": "PTA33445566", "holder_member_state": "PT", "holder_type": "individual", "total_value_eur": 12300.00, "verification_status": "verified"},
    {"wallet_address": "0x7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a66", "holder_tin": "ESA77889900", "holder_member_state": "ES", "holder_type": "business", "total_value_eur": 567000.00, "verification_status": "verified"},
    {"wallet_address": "0x8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b77", "holder_tin": None, "holder_member_state": "ES", "holder_type": "individual", "total_value_eur": 3400.00, "verification_status": "no_tin"},
    {"wallet_address": "0x9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c88", "holder_tin": "BEL44556677", "holder_member_state": "BE", "holder_type": "individual", "total_value_eur": 78000.00, "verification_status": "verified"},
    {"wallet_address": "0xa0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d99", "holder_tin": "NLD55667788", "holder_member_state": "NL", "holder_type": "business", "total_value_eur": 345000.00, "verification_status": "verified"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed DAC8/DAC9 data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(ENTITY_DATA)} reporting entities")
        print(f"[DRY RUN] Would insert {len(REPORTS_DATA)} crypto reports")
        print(f"[DRY RUN] Would insert {len(WALLET_HOLDER_DATA)} wallet holders")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # Insert reporting entities
    for e in ENTITY_DATA:
        cur.execute(
            """INSERT INTO dac_reporting_entity (tin, entity_type, member_state,
               dac8_registered, dac9_registered, status)
               VALUES (%(tin)s, %(entity_type)s, %(member_state)s,
                       %(dac8_registered)s, %(dac9_registered)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            e,
        )

    # Insert reports
    for r in REPORTS_DATA:
        cur.execute(
            """INSERT INTO dac_crypto_report (entity_id, reporting_period, submitted_at,
               status, crypto_transactions_count, wallet_holders_count)
               VALUES (%(entity_id)s, %(reporting_period)s, %(submitted_at)s,
                       %(status)s, %(crypto_transactions_count)s, %(wallet_holders_count)s)""",
            r,
        )

    # Insert wallet holders
    for w in WALLET_HOLDER_DATA:
        cur.execute(
            """INSERT INTO dac_wallet_holder (wallet_address, holder_tin, holder_member_state,
               holder_type, total_value_eur, verification_status)
               VALUES (%(wallet_address)s, %(holder_tin)s, %(holder_member_state)s,
                       %(holder_type)s, %(total_value_eur)s, %(verification_status)s)""",
            w,
        )

    conn.commit()
    total = len(ENTITY_DATA) + len(REPORTS_DATA) + len(WALLET_HOLDER_DATA)
    print(f"OK: {total} registros DAC8/DAC9 insertados ({len(ENTITY_DATA)} entities, {len(REPORTS_DATA)} reports, {len(WALLET_HOLDER_DATA)} wallet holders)")
    conn.close()


if __name__ == "__main__":
    main()
