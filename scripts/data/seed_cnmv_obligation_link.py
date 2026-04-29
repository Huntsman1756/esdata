#!/usr/bin/env python3
"""Seed cnmv_obligation_link — Vinculos entre obligaciones y documentos CNMV.

Uso:
    python scripts/data/seed_cnmv_obligation_link.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

OBLIGATION_LINKS = [
    {
        "documento_referencia": "V0000-26",
        "tipo_obligacion": "informe_anual",
        "nota": "Consulta DGT sobre tipo reducido vinculada a informe anual de IVA",
    },
    {
        "documento_referencia": "VAT-2024-001",
        "tipo_obligacion": "transparencia",
        "nota": "Interpretacion IVA digital services obligacion de transparencia en servicios electronicos",
    },
    {
        "documento_referencia": "VAT-2024-002",
        "tipo_obligacion": "informe_trimestral",
        "nota": "Facturacion electronica obligatoria vinculada a informe trimestral de operaciones",
    },
    {
        "documento_referencia": "IRPF-2024-001",
        "tipo_obligacion": "gobierno_corporativo",
        "nota": "Deducciones vivienda habitual 2024 obligacion de gobierno corporativo en IRPF",
    },
    {
        "documento_referencia": "IRPF-2024-002",
        "tipo_obligacion": "informe_operaciones",
        "nota": "Retenciones autonomos 2024 obligacion de comunicacion de operaciones",
    },
    {
        "documento_referencia": "LIS-2024-001",
        "tipo_obligacion": "compliance",
        "nota": "Deduccion I+D+i 2024 obligacion de compliance en deducciones fiscales",
    },
    {
        "documento_referencia": "V2274-22",
        "tipo_obligacion": "transparencia",
        "nota": "V2274-22 obligacion de transparencia en telecomunicaciones y radiodifusion",
    },
    {
        "documento_referencia": "V1923-24",
        "tipo_obligacion": "informe_anual",
        "nota": "V1923-24 vinculada a informe anual de suministro de gas natural",
    },
    {
        "documento_referencia": "V2691-21",
        "tipo_obligacion": "informe_operaciones",
        "nota": "V2691-21 obligacion de comunicacion de operaciones con dividendos",
    },
    {
        "documento_referencia": "V1387-20",
        "tipo_obligacion": "gobierno_corporativo",
        "nota": "V1387-20 obligacion de gobierno corporativo en construccion",
    },
    {
        "documento_referencia": "V1140-24",
        "tipo_obligacion": "conflictos_interes",
        "nota": "V1140-24 gestion de conflictos de interes en opciones de compra ESOP",
    },
    {
        "documento_referencia": "V2509-20",
        "tipo_obligacion": "informe_anual",
        "nota": "V2509-20 vinculada a informe anual de exencion de vivienda habitual",
    },
    {
        "documento_referencia": "V0228-25",
        "tipo_obligacion": "transparencia",
        "nota": "V0228-25 obligacion de transparencia en residencia fiscal dual",
    },
    {
        "documento_referencia": "V2223-22",
        "tipo_obligacion": "compliance",
        "nota": "V2223-22 obligacion de compliance en doble imposicion internacional",
    },
    {
        "documento_referencia": "V0745-20",
        "tipo_obligacion": "informe_trimestral",
        "nota": "V0745-20 vinculada a informe trimestral de hosting y alojamiento web",
    },
    {
        "documento_referencia": "V1902-23",
        "tipo_obligacion": "compliance",
        "nota": "V1902-23 obligacion de compliance en deducciones I+D+i en el Impuesto sobre Sociedades",
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed cnmv_obligation_link")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in OBLIGATION_LINKS:
        cur.execute(
            """INSERT INTO cnmv_obligation_link (documento_referencia, tipo_obligacion, nota)
               VALUES (%(documento_referencia)s, %(tipo_obligacion)s, %(nota)s)
               ON CONFLICT DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} cnmv_obligation_link records inserted")
    conn.close()


if __name__ == "__main__":
    main()
