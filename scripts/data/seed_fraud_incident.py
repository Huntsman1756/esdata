#!/usr/bin/env python3
"""Seed fraud_incident — Incidentes de fraude para compliance PBC.

Uso:
    python scripts/data/seed_fraud_incident.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

FRAUD_INCIDENTS = [
    {
        "entity_id": 1,
        "incident_date": datetime.now().date(),
        "description": "Operacion sospechosa de transferencia internacional sin justificante",
        "amount_eur": 45000.00,
        "status": "under_investigation",
        "resolution_date": None,
        "regulatory_notification": True,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 1,
        "incident_date": datetime.now().date(),
        "description": "Posible structuring de operaciones para evitar reporte",
        "amount_eur": 28000.00,
        "status": "resolved",
        "resolution_date": datetime.now().date(),
        "regulatory_notification": True,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 2,
        "incident_date": datetime.now().date(),
        "description": "Cuenta de cliente con actividad incoherente con perfil",
        "amount_eur": 120000.00,
        "status": "under_investigation",
        "resolution_date": None,
        "regulatory_notification": True,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 2,
        "incident_date": datetime.now().date(),
        "description": "Operacion de trading con margen sospechosamente rapida",
        "amount_eur": 67000.00,
        "status": "resolved",
        "resolution_date": datetime.now().date(),
        "regulatory_notification": False,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 3,
        "incident_date": datetime.now().date(),
        "description": "Identidad de cliente verificada con documentos falsificados",
        "amount_eur": 0.00,
        "status": "closed",
        "resolution_date": datetime.now().date(),
        "regulatory_notification": True,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 3,
        "incident_date": datetime.now().date(),
        "description": "Transaccion con wallet de mixer o tumbling service",
        "amount_eur": 89000.00,
        "status": "under_investigation",
        "resolution_date": None,
        "regulatory_notification": True,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 4,
        "incident_date": datetime.now().date(),
        "description": "Cliente PEP sin debida diligencia reforzada",
        "amount_eur": 250000.00,
        "status": "open",
        "resolution_date": None,
        "regulatory_notification": False,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 4,
        "incident_date": datetime.now().date(),
        "description": "Operacion cruzando jurisdiccion de alto riesgo sin reporte",
        "amount_eur": 55000.00,
        "status": "resolved",
        "resolution_date": datetime.now().date(),
        "regulatory_notification": True,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 5,
        "incident_date": datetime.now().date(),
        "description": "Actividad de trading algoritmico con patrones de wash trading",
        "amount_eur": 340000.00,
        "status": "open",
        "resolution_date": None,
        "regulatory_notification": True,
        "created_at": datetime.now(),
    },
    {
        "entity_id": 5,
        "incident_date": datetime.now().date(),
        "description": "Solicitud de retiro incoherente con historial de ingresos",
        "amount_eur": 15000.00,
        "status": "closed",
        "resolution_date": datetime.now().date(),
        "regulatory_notification": False,
        "created_at": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed fraud_incident")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in FRAUD_INCIDENTS:
        cur.execute(
            """INSERT INTO fraud_incident (entity_id, incident_date, description,
               amount_eur, status, resolution_date, regulatory_notification, created_at)
               VALUES (%(entity_id)s, %(incident_date)s, %(description)s,
                       %(amount_eur)s, %(status)s, %(resolution_date)s,
                       %(regulatory_notification)s, %(created_at)s)
               ON CONFLICT (entity_id, incident_date, description) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} fraud_incident records inserted")
    conn.close()


if __name__ == "__main__":
    main()
