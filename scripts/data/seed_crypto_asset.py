#!/usr/bin/env python3
"""Seed crypto_asset — Activos cripto relevantes para DAC8/DAC9.

Uso:
    python scripts/data/seed_crypto_asset.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

CRYPTO_ASSETS = [
    {
        "asset_type": "cryptocurrency",
        "reference_uid": "BTC",
        "issuer_jurisdiction": None,
        "is_sha": False,
        "market_value_eur": 85000.00,
        "holders_count": 10000000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "cryptocurrency",
        "reference_uid": "ETH",
        "issuer_jurisdiction": None,
        "is_sha": False,
        "market_value_eur": 2500.00,
        "holders_count": 200000000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "stablecoin",
        "reference_uid": "USDT",
        "issuer_jurisdiction": "KY",
        "is_sha": True,
        "market_value_eur": 1.00,
        "holders_count": 50000000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "stablecoin",
        "reference_uid": "USDC",
        "issuer_jurisdiction": "US",
        "is_sha": True,
        "market_value_eur": 1.00,
        "holders_count": 40000000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "stablecoin",
        "reference_uid": "EURC",
        "issuer_jurisdiction": "LU",
        "is_sha": True,
        "market_value_eur": 1.08,
        "holders_count": 500000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "security_token",
        "reference_uid": "tBTC",
        "issuer_jurisdiction": "CH",
        "is_sha": True,
        "market_value_eur": 84000.00,
        "holders_count": 5000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "cryptocurrency",
        "reference_uid": "SOL",
        "issuer_jurisdiction": None,
        "is_sha": False,
        "market_value_eur": 145.00,
        "holders_count": 15000000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "cryptocurrency",
        "reference_uid": "XRP",
        "issuer_jurisdiction": None,
        "is_sha": False,
        "market_value_eur": 0.55,
        "holders_count": 30000000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "defi_token",
        "reference_uid": "UNI",
        "issuer_jurisdiction": None,
        "is_sha": False,
        "market_value_eur": 7.50,
        "holders_count": 400000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "asset_type": "defi_token",
        "reference_uid": "LINK",
        "issuer_jurisdiction": None,
        "is_sha": False,
        "market_value_eur": 15.00,
        "holders_count": 600000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed crypto_asset")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in CRYPTO_ASSETS:
        cur.execute(
            """INSERT INTO crypto_asset (asset_type, reference_uid, issuer_jurisdiction,
               is_sha, market_value_eur, holders_count, status, created_at, updated_at)
               VALUES (%(asset_type)s, %(reference_uid)s, %(issuer_jurisdiction)s,
                       %(is_sha)s, %(market_value_eur)s, %(holders_count)s, %(status)s,
                       %(created_at)s, %(updated_at)s)
               ON CONFLICT (reference_uid) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} crypto_asset records inserted")
    conn.close()


if __name__ == "__main__":
    main()
