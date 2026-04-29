#!/usr/bin/env python3
"""Seed fraud_risk_assessment — Evaluaciones de riesgo de fraude.

Uso:
    python scripts/data/seed_fraud_risk_assessment.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

FRAUD_RISK_ASSESSMENTS = [
    {
        "entity_id": 1,
        "assessment_date": datetime.now().date(),
        "risk_areas": "Transferencias internacionales, structuring de operaciones",
        "mitigation_measures": "Monitoreo automatizado, thresholds de reporte reducidos",
        "next_review_date": datetime.now().date() + timedelta(days=90),
        "created_at": datetime.now(),
    },
    {
        "entity_id": 2,
        "assessment_date": datetime.now().date(),
        "risk_areas": "Trading algoritmico, operaciones cruzadas",
        "mitigation_measures": "ML models, monitoring en tiempo real",
        "next_review_date": datetime.now().date() + timedelta(days=90),
        "created_at": datetime.now(),
    },
    {
        "entity_id": 3,
        "assessment_date": datetime.now().date(),
        "risk_areas": "KYC deficiente, PEP monitoring",
        "mitigation_measures": "Reforzar KYC, screening PEP automatizado",
        "next_review_date": datetime.now().date() + timedelta(days=90),
        "created_at": datetime.now(),
    },
    {
        "entity_id": 4,
        "assessment_date": datetime.now().date(),
        "risk_areas": "Sin programa de compliance establecido",
        "mitigation_measures": "Implementar programa basico, designar compliance officer",
        "next_review_date": datetime.now().date() + timedelta(days=90),
        "created_at": datetime.now(),
    },
    {
        "entity_id": 5,
        "assessment_date": datetime.now().date(),
        "risk_areas": "Wash trading, market manipulation, crypto integration",
        "mitigation_measures": "Blockchain analytics, pattern detection, enhanced monitoring",
        "next_review_date": datetime.now().date() + timedelta(days=90),
        "created_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed fraud_risk_assessment")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in FRAUD_RISK_ASSESSMENTS:
        cur.execute(
            """INSERT INTO fraud_risk_assessment (entity_id, assessment_date,
               risk_areas, mitigation_measures, next_review_date, created_at)
               VALUES (%(entity_id)s, %(assessment_date)s, %(risk_areas)s,
                       %(mitigation_measures)s, %(next_review_date)s, %(created_at)s)
               ON CONFLICT (entity_id, assessment_date) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} fraud_risk_assessment records inserted")
    conn.close()


if __name__ == "__main__":
    main()
