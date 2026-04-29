#!/usr/bin/env python3
"""Seed fraud_prevention_program — Programas de prevencion de fraude.

Uso:
    python scripts/data/seed_fraud_prevention_program.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

FRAUD_PROGRAMS = [
    {
        "entity_id": 1,
        "code_of_conduct": True,
        "internal_reporting_system": True,
        "training_schedule": "Anual",
        "audit_frequency": "Semestral",
        "compliance_officer_name": "Dra. Maria Garcia",
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "entity_id": 2,
        "code_of_conduct": True,
        "internal_reporting_system": True,
        "training_schedule": "Trimestral",
        "audit_frequency": "Mensual",
        "compliance_officer_name": "Dr. Carlos Lopez",
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "entity_id": 3,
        "code_of_conduct": True,
        "internal_reporting_system": False,
        "training_schedule": "Anual",
        "audit_frequency": "Anual",
        "compliance_officer_name": "Lic. Ana Fernandez",
        "status": "active",
        "created_at": datetime.now(),
    },
    {
        "entity_id": 4,
        "code_of_conduct": False,
        "internal_reporting_system": False,
        "training_schedule": None,
        "audit_frequency": None,
        "compliance_officer_name": None,
        "status": "pending",
        "created_at": datetime.now(),
    },
    {
        "entity_id": 5,
        "code_of_conduct": True,
        "internal_reporting_system": True,
        "training_schedule": "Mensual",
        "audit_frequency": "Trimestral",
        "compliance_officer_name": "Dr. Pablo Ruiz",
        "status": "active",
        "created_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed fraud_prevention_program")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in FRAUD_PROGRAMS:
        cur.execute(
            """INSERT INTO fraud_prevention_program (entity_id, code_of_conduct,
               internal_reporting_system, training_schedule, audit_frequency,
               compliance_officer_name, status, created_at)
               VALUES (%(entity_id)s, %(code_of_conduct)s, %(internal_reporting_system)s,
                       %(training_schedule)s, %(audit_frequency)s,
                       %(compliance_officer_name)s, %(status)s, %(created_at)s)
               ON CONFLICT (entity_id) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} fraud_prevention_program records inserted")
    conn.close()


if __name__ == "__main__":
    main()
