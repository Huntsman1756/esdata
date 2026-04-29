#!/usr/bin/env python3
"""Seed crypto_transaction — Transacciones de criptoactivos para DAC8/DAC9.

Uso:
    python scripts/data/seed_crypto_transaction.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

CRYPTO_TRANSACTIONS = [
    {
        "sender_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "receiver_wallet": "0xAb5801a7D398351b8bE11C439e05C5b3259ae9b",
        "sender_jurisdiction": "ES",
        "receiver_jurisdiction": "FR",
        "asset_type": "cryptocurrency",
        "amount": 2.5,
        "value_eur": 212500.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q1",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
        "receiver_wallet": "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
        "sender_jurisdiction": "ES",
        "receiver_jurisdiction": "DE",
        "asset_type": "stablecoin",
        "amount": 50000.00,
        "value_eur": 50000.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q1",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
        "receiver_wallet": "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
        "sender_jurisdiction": "IE",
        "receiver_jurisdiction": "LU",
        "asset_type": "cryptocurrency",
        "amount": 10.0,
        "value_eur": 850000.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q2",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "receiver_wallet": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "sender_jurisdiction": "DE",
        "receiver_jurisdiction": "NL",
        "asset_type": "defi_token",
        "amount": 5000.00,
        "value_eur": 37500.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q1",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "0xAb5801a7D398351b8bE11C439e05C5b3259ae9b",
        "receiver_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "sender_jurisdiction": "FR",
        "receiver_jurisdiction": "ES",
        "asset_type": "stablecoin",
        "amount": 25000.00,
        "value_eur": 25000.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q2",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        "receiver_wallet": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
        "sender_jurisdiction": "LU",
        "receiver_jurisdiction": "NL",
        "asset_type": "cryptocurrency",
        "amount": 0.5,
        "value_eur": 42500.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q1",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "receiver_wallet": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
        "sender_jurisdiction": "ES",
        "receiver_jurisdiction": "PT",
        "asset_type": "cryptocurrency",
        "amount": 1.0,
        "value_eur": 85000.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q2",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
        "receiver_wallet": "0xAb5801a7D398351b8bE11C439e05C5b3259ae9b",
        "sender_jurisdiction": "DE",
        "receiver_jurisdiction": "ES",
        "asset_type": "stablecoin",
        "amount": 100000.00,
        "value_eur": 100000.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q1",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
        "receiver_wallet": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "sender_jurisdiction": "IE",
        "receiver_jurisdiction": "DE",
        "asset_type": "defi_token",
        "amount": 2000.00,
        "value_eur": 30000.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q2",
        "status": "pending",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "sender_wallet": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "receiver_wallet": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "sender_jurisdiction": "NL",
        "receiver_jurisdiction": "FR",
        "asset_type": "cryptocurrency",
        "amount": 5.0,
        "value_eur": 425000.00,
        "timestamp": datetime.now(),
        "reporting_period": "2025-Q1",
        "status": "completed",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed crypto_transaction")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in CRYPTO_TRANSACTIONS:
        cur.execute(
            """INSERT INTO crypto_transaction (sender_wallet, receiver_wallet,
               sender_jurisdiction, receiver_jurisdiction, asset_type, amount,
               value_eur, timestamp, reporting_period, status, created_at, updated_at)
               VALUES (%(sender_wallet)s, %(receiver_wallet)s, %(sender_jurisdiction)s,
                       %(receiver_jurisdiction)s, %(asset_type)s, %(amount)s,
                       %(value_eur)s, %(timestamp)s, %(reporting_period)s, %(status)s,
                       %(created_at)s, %(updated_at)s)
               ON CONFLICT (sender_wallet, receiver_wallet, timestamp) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} crypto_transaction records inserted")
    conn.close()


if __name__ == "__main__":
    main()
