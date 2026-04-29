#!/usr/bin/env python3
"""Seed dac_crypto_report — Reportes de criptoactivos DAC8.

Uso:
    python scripts/data/seed_dac_crypto_report.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

CRYPTO_REPORTS = [
    {
        "reporting_period": "2025-Q1",
        "submitted_at": datetime.now(),
        "status": "submitted",
        "crypto_transactions_count": 1250,
        "wallet_holders_count": 85,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q2",
        "submitted_at": datetime.now(),
        "status": "submitted",
        "crypto_transactions_count": 1480,
        "wallet_holders_count": 92,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q1",
        "submitted_at": datetime.now(),
        "status": "submitted",
        "crypto_transactions_count": 3200,
        "wallet_holders_count": 210,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q1",
        "submitted_at": datetime.now(),
        "status": "submitted",
        "crypto_transactions_count": 890,
        "wallet_holders_count": 45,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q1",
        "submitted_at": datetime.now(),
        "status": "submitted",
        "crypto_transactions_count": 5600,
        "wallet_holders_count": 340,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q1",
        "submitted_at": datetime.now(),
        "status": "draft",
        "crypto_transactions_count": 420,
        "wallet_holders_count": 28,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q1",
        "submitted_at": datetime.now(),
        "status": "submitted",
        "crypto_transactions_count": 2100,
        "wallet_holders_count": 156,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q1",
        "submitted_at": datetime.now(),
        "status": "submitted",
        "crypto_transactions_count": 1750,
        "wallet_holders_count": 120,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q1",
        "submitted_at": datetime.now(),
        "status": "pending_review",
        "crypto_transactions_count": 680,
        "wallet_holders_count": 35,
        "created_at": datetime.now(),
    },
    {
        "reporting_period": "2025-Q1",
        "submitted_at": None,
        "status": "not_started",
        "crypto_transactions_count": None,
        "wallet_holders_count": None,
        "created_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed dac_crypto_report")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    cur.execute("SELECT id FROM dac_reporting_entity ORDER BY id")
    entity_ids = [row[0] for row in cur.fetchall()]

    count = 0
    for i, d in enumerate(CRYPTO_REPORTS):
        if i >= len(entity_ids):
            continue
        entity_id = entity_ids[i]
        cur.execute(
            """INSERT INTO dac_crypto_report (entity_id, reporting_period, submitted_at,
               status, crypto_transactions_count, wallet_holders_count, created_at)
               VALUES (%(entity_id)s, %(reporting_period)s, %(submitted_at)s,
                       %(status)s, %(crypto_transactions_count)s, %(wallet_holders_count)s,
                       %(created_at)s)
               ON CONFLICT (entity_id, reporting_period) DO NOTHING""",
            {
                "entity_id": entity_id,
                "reporting_period": d["reporting_period"],
                "submitted_at": d["submitted_at"],
                "status": d["status"],
                "crypto_transactions_count": d["crypto_transactions_count"],
                "wallet_holders_count": d["wallet_holders_count"],
                "created_at": d["created_at"],
            },
        )
        count += 1

    conn.commit()
    print(f"OK: {count} dac_crypto_report records inserted")
    conn.close()


if __name__ == "__main__":
    main()
