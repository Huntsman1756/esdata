#!/usr/bin/env python3
"""Seed xbrl_filing — Depositos XBRL de companias.

Uso:
    python scripts/data/seed_xbrl_filing.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

XBRL_FILINGS = [
    {
        "source_name": "CNMV",
        "source_path": "documentos/2024/ANUAL_ES0130001035_2024.xlsx",
        "entity_identifier": "ES0130001035",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "filing_type": "annual",
        "created_at": datetime.now(),
    },
    {
        "source_name": "CNMV",
        "source_path": "documentos/2024/TRIM_ES0130001035_2024Q1.xlsx",
        "entity_identifier": "ES0130001035",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 3, 31).date(),
        "filing_type": "quarterly",
        "created_at": datetime.now(),
    },
    {
        "source_name": "CNMV",
        "source_path": "documentos/2024/TRIM_ES0130001035_2024Q2.xlsx",
        "entity_identifier": "ES0130001035",
        "period_start": datetime(2024, 4, 1).date(),
        "period_end": datetime(2024, 6, 30).date(),
        "filing_type": "quarterly",
        "created_at": datetime.now(),
    },
    {
        "source_name": "EDGAR",
        "source_path": "edgar/2024/0001234567_2024_10K.xlsx",
        "entity_identifier": "0001234567",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "filing_type": "annual",
        "created_at": datetime.now(),
    },
    {
        "source_name": "EDGAR",
        "source_path": "edgar/2024/0001234567_2024_10Q.xlsx",
        "entity_identifier": "0001234567",
        "period_start": datetime(2024, 4, 1).date(),
        "period_end": datetime(2024, 6, 30).date(),
        "filing_type": "quarterly",
        "created_at": datetime.now(),
    },
    {
        "source_name": "CNMV",
        "source_path": "documentos/2024/ANUAL_ES0123456015_2024.xlsx",
        "entity_identifier": "ES0123456015",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "filing_type": "annual",
        "created_at": datetime.now(),
    },
    {
        "source_name": "CNMV",
        "source_path": "documentos/2024/ESG_ES0130001035_2024.xlsx",
        "entity_identifier": "ES0130001035",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "filing_type": "esg",
        "created_at": datetime.now(),
    },
    {
        "source_name": "EDGAR",
        "source_path": "edgar/2024/0009876543_2024_ESG.xlsx",
        "entity_identifier": "0009876543",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "filing_type": "esg",
        "created_at": datetime.now(),
    },
    {
        "source_name": "CNMV",
        "source_path": "documentos/2025/TRIM_ES0130001035_2025Q1.xlsx",
        "entity_identifier": "ES0130001035",
        "period_start": datetime(2025, 1, 1).date(),
        "period_end": datetime(2025, 3, 31).date(),
        "filing_type": "quarterly",
        "created_at": datetime.now(),
    },
    {
        "source_name": "EDGAR",
        "source_path": "edgar/2024/0001234567_2024_8K.xlsx",
        "entity_identifier": "0001234567",
        "period_start": None,
        "period_end": None,
        "filing_type": "current",
        "created_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed xbrl_filing")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in XBRL_FILINGS:
        cur.execute(
            """INSERT INTO xbrl_filing (source_name, source_path, entity_identifier,
               period_start, period_end, filing_type, created_at)
               VALUES (%(source_name)s, %(source_path)s, %(entity_identifier)s,
                       %(period_start)s, %(period_end)s, %(filing_type)s, %(created_at)s)
               ON CONFLICT (source_path) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} xbrl_filing records inserted")
    conn.close()


if __name__ == "__main__":
    main()
