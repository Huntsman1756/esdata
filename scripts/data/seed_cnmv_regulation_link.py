#!/usr/bin/env python3
"""Seed cnmv_regulation_link — Vinculos entre regulaciones y documentos CNMV.

Uso:
    python scripts/data/seed_cnmv_regulation_link.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

REGULATION_LINKS = [
    {
        "documento_referencia": "V0000-26",
        "regulacion_id": "RD-1065-2007",
        "relacion_tipo": "aplica",
        "nota": "Consulta DGT sobre tipo reducido aplica RD-1065/2007 del II RD",
    },
    {
        "documento_referencia": "VAT-2024-001",
        "regulacion_id": "RD-1-2021",
        "relacion_tipo": "aplica",
        "nota": "Interpretacion IVA digital services aplica RD-1/2021 de factura electronica",
    },
    {
        "documento_referencia": "VAT-2024-002",
        "regulacion_id": "RD-1619-2012",
        "relacion_tipo": "deriva_de",
        "nota": "Facturacion electronica obligatoria deriva de RD-1619/2012 del regimen contable",
    },
    {
        "documento_referencia": "IRPF-2024-001",
        "regulacion_id": "RD-439-2023",
        "relacion_tipo": "aplica",
        "nota": "Deducciones vivienda habitual 2024 aplica RD-439/2023 de la IRPF",
    },
    {
        "documento_referencia": "IRPF-2024-002",
        "regulacion_id": "RD-439-2023",
        "relacion_tipo": "aplica",
        "nota": "Retenciones autonomos 2024 aplica RD-439/2023 de la IRPF",
    },
    {
        "documento_referencia": "LIS-2024-001",
        "regulacion_id": "RD-1777-2004",
        "relacion_tipo": "aplica",
        "nota": "Deduccion I+D+i 2024 aplica RD-1777/2004 del regimen de las grandes empresas",
    },
    {
        "documento_referencia": "V2274-22",
        "regulacion_id": "RD-1619-2012",
        "relacion_tipo": "deriva_de",
        "nota": "V2274-22 deriva de RD-1619/2012 del regimen contable para telecomunicaciones",
    },
    {
        "documento_referencia": "V1923-24",
        "regulacion_id": "RD-1065-2007",
        "relacion_tipo": "aplica",
        "nota": "V1923-24 aplica RD-1065/2007 del II RD en suministro de gas natural",
    },
    {
        "documento_referencia": "V2691-21",
        "regulacion_id": "RD-439-2023",
        "relacion_tipo": "aplica",
        "nota": "V2691-21 aplica RD-439/2023 de la IRPF en dividendos extranjeros",
    },
    {
        "documento_referencia": "V1387-20",
        "regulacion_id": "RD-1065-2007",
        "relacion_tipo": "aplica",
        "nota": "V1387-20 aplica RD-1065/2007 del II RD en construccion",
    },
    {
        "documento_referencia": "V1140-24",
        "regulacion_id": "RD-1777-2004",
        "relacion_tipo": "deriva_de",
        "nota": "V1140-24 deriva de RD-1777/2004 del regimen de las grandes empresas en ESOP",
    },
    {
        "documento_referencia": "V2509-20",
        "regulacion_id": "RD-439-2023",
        "relacion_tipo": "aplica",
        "nota": "V2509-20 aplica RD-439/2023 de la IRPF en exencion de vivienda habitual",
    },
    {
        "documento_referencia": "V0228-25",
        "regulacion_id": "RD-560-2025",
        "relacion_tipo": "aplica",
        "nota": "V0228-25 aplica RD-560/2025 de residencia fiscal en actividad dual",
    },
    {
        "documento_referencia": "V2223-22",
        "regulacion_id": "RD-1777-2004",
        "relacion_tipo": "aplica",
        "nota": "V2223-22 aplica RD-1777/2004 del regimen de las grandes empresas en doble imposicion",
    },
    {
        "documento_referencia": "V0745-20",
        "regulacion_id": "RD-1619-2012",
        "relacion_tipo": "deriva_de",
        "nota": "V0745-20 deriva de RD-1619/2012 del regimen contable para hosting y alojamiento web",
    },
    {
        "documento_referencia": "V1902-23",
        "regulacion_id": "RD-1777-2004",
        "relacion_tipo": "aplica",
        "nota": "V1902-23 aplica RD-1777/2004 del regimen de las grandes empresas en I+D+i",
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed cnmv_regulation_link")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in REGULATION_LINKS:
        cur.execute(
            """INSERT INTO cnmv_regulation_link (documento_referencia, regulacion_id,
               relacion_tipo, nota)
               VALUES (%(documento_referencia)s, %(regulacion_id)s,
                       %(relacion_tipo)s, %(nota)s)
               ON CONFLICT DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} cnmv_regulation_link records inserted")
    conn.close()


if __name__ == "__main__":
    main()
