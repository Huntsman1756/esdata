#!/usr/bin/env python3
"""Seed dac_reporting_entity — Entidades de declaracion DAC8/DAC9.

Uso:
    python scripts/data/seed_dac_reporting_entity.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

REPORTING_ENTITIES = [
    {
        "tin": "ES12345678A",
        "entity_type": "reporting_fi",
        "member_state": "ES",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "tin": "ES87654321B",
        "entity_type": "custodian_broker",
        "member_state": "ES",
        "dac8_registered": True,
        "dac9_registered": False,
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "tin": "FR12345678901",
        "entity_type": "reporting_fi",
        "member_state": "FR",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "tin": "DE123456789",
        "entity_type": "payment_platform",
        "member_state": "DE",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "tin": "IE1234567T",
        "entity_type": "investment_fund",
        "member_state": "IE",
        "dac8_registered": True,
        "dac9_registered": False,
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "tin": "LU12345678",
        "entity_type": "custodian_broker",
        "member_state": "LU",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "tin": "NL123456789B01",
        "entity_type": "reporting_fi",
        "member_state": "NL",
        "dac8_registered": True,
        "dac9_registered": False,
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "tin": "PT123456789",
        "entity_type": "payment_platform",
        "member_state": "PT",
        "dac8_registered": True,
        "dac9_registered": True,
        "status": "pending",
        "created_at": datetime.now(),
    },
    {
        "tin": "IT12345678901",
        "entity_type": "custodian_broker",
        "member_state": "IT",
        "dac8_registered": False,
        "dac9_registered": False,
        "status": "pending",
        "created_at": datetime.now(),
    },
    {
        "tin": "US123456789",
        "entity_type": "foreign_platform",
        "member_state": "US",
        "dac8_registered": False,
        "dac9_registered": False,
        "status": "active",
        "created_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed dac_reporting_entity")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in REPORTING_ENTITIES:
        cur.execute(
            """INSERT INTO dac_reporting_entity (tin, entity_type, member_state,
               dac8_registered, dac9_registered, status, created_at)
               VALUES (%(tin)s, %(entity_type)s, %(member_state)s,
                       %(dac8_registered)s, %(dac9_registered)s, %(status)s, %(created_at)s)
               ON CONFLICT (tin) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} dac_reporting_entity records inserted")
    conn.close()


if __name__ == "__main__":
    main()
