#!/usr/bin/env python3
"""Seed xbrl_fact — Hechos XBRL extraidos de depositos.

Uso:
    python scripts/data/seed_xbrl_fact.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

XBRL_FACTS = [
    {
        "source_path": "documentos/2024/ANUAL_ES0130001035_2024.xlsx",
        "concept": "esga:BalanceTotalActivos",
        "value_raw": "1500000000",
        "value_numeric": 1500000000.00,
        "unit": "EUR",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "ES0130001035",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "documentos/2024/ANUAL_ES0130001035_2024.xlsx",
        "concept": "esga:PatrimonioNetoTotal",
        "value_raw": "450000000",
        "value_numeric": 450000000.00,
        "unit": "EUR",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "ES0130001035",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "documentos/2024/ANUAL_ES0130001035_2024.xlsx",
        "concept": "esga:ResultadoNetoPeriodo",
        "value_raw": "85000000",
        "value_numeric": 85000000.00,
        "unit": "EUR",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "ES0130001035",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "documentos/2024/ANUAL_ES0130001035_2024.xlsx",
        "concept": "esga:ActosComercialesPartesRelacionadas",
        "value_raw": "12000000",
        "value_numeric": 12000000.00,
        "unit": "EUR",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "ES0130001035",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "documentos/2024/TRIM_ES0130001035_2024Q1.xlsx",
        "concept": "esga:IngresosOperativosTrimestre",
        "value_raw": "22000000",
        "value_numeric": 22000000.00,
        "unit": "EUR",
        "context_ref": "2024-03-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 3, 31).date(),
        "entity_identifier": "ES0130001035",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "documentos/2024/TRIM_ES0130001035_2024Q1.xlsx",
        "concept": "esga:MargenEBITDATrimestral",
        "value_raw": "0.35",
        "value_numeric": 0.35,
        "unit": "pure",
        "context_ref": "2024-03-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 3, 31).date(),
        "entity_identifier": "ES0130001035",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "edgar/2024/0001234567_2024_10K.xlsx",
        "concept": "us-gaap:Assets",
        "value_raw": "52000000000",
        "value_numeric": 52000000000.00,
        "unit": "USD",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "0001234567",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "edgar/2024/0001234567_2024_10K.xlsx",
        "concept": "us-gaap:NetIncomeLoss",
        "value_raw": "8500000000",
        "value_numeric": 8500000000.00,
        "unit": "USD",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "0001234567",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "edgar/2024/0001234567_2024_10K.xlsx",
        "concept": "us-gaap:EarningsPerShareBasic",
        "value_raw": "12.45",
        "value_numeric": 12.45,
        "unit": "USD/sha",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "0001234567",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "documentos/2024/ESG_ES0130001035_2024.xlsx",
        "concept": "esga:EmisionesGasesEfectoInvernaderoTotal",
        "value_raw": "45000",
        "value_numeric": 45000.00,
        "unit": "tonneCO2e",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "ES0130001035",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "documentos/2024/ESG_ES0130001035_2024.xlsx",
        "concept": "esga:GastoInvestigacionDesarrollo",
        "value_raw": "15000000",
        "value_numeric": 15000000.00,
        "unit": "EUR",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "ES0130001035",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
    {
        "source_path": "edgar/2024/0009876543_2024_ESG.xlsx",
        "concept": "sustainability:Scope1Emissions",
        "value_raw": "25000",
        "value_numeric": 25000.00,
        "unit": "tonneCO2e",
        "context_ref": "2024-12-31",
        "period_start": datetime(2024, 1, 1).date(),
        "period_end": datetime(2024, 12, 31).date(),
        "entity_identifier": "0009876543",
        "decimals": "INF",
        "created_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed xbrl_fact")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    cur.execute("SELECT id, source_path FROM xbrl_filing")
    filing_map = {row[1]: row[0] for row in cur.fetchall()}

    count = 0
    for d in XBRL_FACTS:
        source_path = d.pop("source_path")
        filing_id = filing_map.get(source_path)
        if filing_id is None:
            continue
        d["filing_id"] = filing_id
        cur.execute(
            """INSERT INTO xbrl_fact (filing_id, concept, value_raw, value_numeric,
               unit, context_ref, period_start, period_end, entity_identifier,
               decimals, created_at)
               VALUES (%(filing_id)s, %(concept)s, %(value_raw)s, %(value_numeric)s,
                       %(unit)s, %(context_ref)s, %(period_start)s, %(period_end)s,
                       %(entity_identifier)s, %(decimals)s, %(created_at)s)
               ON CONFLICT DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} xbrl_fact records inserted")
    conn.close()


if __name__ == "__main__":
    main()
