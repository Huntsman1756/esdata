#!/usr/bin/env python3
"""Seed dac_wallet_holder — Titulares de wallets vinculados a reportes DAC crypto.

Uso:
    python scripts/data/seed_dac_wallet_holder.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

WALLET_HOLDERS = [
    {
        "report_index": 0,
        "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "holder_tin": "ES12345678A",
        "holder_member_state": "ES",
        "holder_type": "individual",
        "total_value_eur": 125000.50,
        "verification_status": "verified",
        "created_at": datetime.now(),
    },
    {
        "report_index": 0,
        "wallet_address": "0xAb5801a7D398351b8bE11C439e05C5b3259ae9b",
        "holder_tin": "ES12345678A",
        "holder_member_state": "ES",
        "holder_type": "individual",
        "total_value_eur": 45000.00,
        "verification_status": "verified",
        "created_at": datetime.now(),
    },
    {
        "report_index": 0,
        "wallet_address": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
        "holder_tin": "FR12345678901",
        "holder_member_state": "FR",
        "holder_type": "entity",
        "total_value_eur": 890000.75,
        "verification_status": "verified",
        "created_at": datetime.now(),
    },
    {
        "report_index": 1,
        "wallet_address": "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
        "holder_tin": None,
        "holder_member_state": None,
        "holder_type": "unknown",
        "total_value_eur": 5000.00,
        "verification_status": "pending",
        "created_at": datetime.now(),
    },
    {
        "report_index": 1,
        "wallet_address": "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
        "holder_tin": "DE123456789",
        "holder_member_state": "DE",
        "holder_type": "individual",
        "total_value_eur": 230000.00,
        "verification_status": "verified",
        "created_at": datetime.now(),
    },
    {
        "report_index": 1,
        "wallet_address": "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
        "holder_tin": "IE1234567T",
        "holder_member_state": "IE",
        "holder_type": "entity",
        "total_value_eur": 1500000.00,
        "verification_status": "verified",
        "created_at": datetime.now(),
    },
    {
        "report_index": 2,
        "wallet_address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        "holder_tin": "LU12345678",
        "holder_member_state": "LU",
        "holder_type": "entity",
        "total_value_eur": 75000.25,
        "verification_status": "verified",
        "created_at": datetime.now(),
    },
    {
        "report_index": 2,
        "wallet_address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
        "holder_tin": "NL123456789B01",
        "holder_member_state": "NL",
        "holder_type": "individual",
        "total_value_eur": 32000.00,
        "verification_status": "pending",
        "created_at": datetime.now(),
    },
    {
        "report_index": 2,
        "wallet_address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "holder_tin": "PT123456789",
        "holder_member_state": "PT",
        "holder_type": "entity",
        "total_value_eur": 410000.00,
        "verification_status": "verified",
        "created_at": datetime.now(),
    },
    {
        "report_index": 2,
        "wallet_address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "holder_tin": "US123456789",
        "holder_member_state": "US",
        "holder_type": "entity",
        "total_value_eur": 2500000.00,
        "verification_status": "verified",
        "created_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed dac_wallet_holder")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    cur.execute("SELECT id FROM dac_crypto_report ORDER BY id")
    report_ids = [row[0] for row in cur.fetchall()]

    count = 0
    for d in WALLET_HOLDERS:
        report_idx = d.pop("report_index")
        if report_idx >= len(report_ids):
            continue
        report_id = report_ids[report_idx]
        cur.execute(
            """INSERT INTO dac_wallet_holder (report_id, wallet_address, holder_tin,
               holder_member_state, holder_type, total_value_eur, verification_status,
               created_at)
               VALUES (%(report_id)s, %(wallet_address)s, %(holder_tin)s,
                       %(holder_member_state)s, %(holder_type)s, %(total_value_eur)s,
                       %(verification_status)s, %(created_at)s)
               ON CONFLICT (wallet_address) DO NOTHING""",
            {
                "report_id": report_id,
                "wallet_address": d["wallet_address"],
                "holder_tin": d["holder_tin"],
                "holder_member_state": d["holder_member_state"],
                "holder_type": d["holder_type"],
                "total_value_eur": d["total_value_eur"],
                "verification_status": d["verification_status"],
                "created_at": d["created_at"],
            },
        )
        count += 1

    conn.commit()
    print(f"OK: {count} dac_wallet_holder records inserted")
    conn.close()


if __name__ == "__main__":
    main()
