#!/usr/bin/env python3
"""Seed irs_dta_convention — Convenios de doble tributacion (DTA).

Uso:
    python scripts/data/seed_irs_dta_convention.py [--database-url URL]
"""

import argparse
import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

CONVENTIONS = [
    {
        "codigo": "DTA-USA-001",
        "pais_origen": "Estados Unidos",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Estados Unidos para evitar la doble tributacion",
        "fecha_firma": "1990-10-05",
        "fecha_vigencia": "1992-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1991-28645",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-FRA-001",
        "pais_origen": "Francia",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Francia para evitar la doble tributacion",
        "fecha_firma": "1990-01-17",
        "fecha_vigencia": "1991-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1990-28345",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-DEU-001",
        "pais_origen": "Alemania",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Alemania para evitar la doble tributacion",
        "fecha_firma": "1975-03-07",
        "fecha_vigencia": "1976-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1975-22134",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-GBR-001",
        "pais_origen": "Reino Unido",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Reino Unido para evitar la doble tributacion",
        "fecha_firma": "1980-06-04",
        "fecha_vigencia": "1981-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1980-15678",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-MEX-001",
        "pais_origen": "Mexico",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Mexico para evitar la doble tributacion",
        "fecha_firma": "1995-06-29",
        "fecha_vigencia": "1997-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1996-22345",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-BRA-001",
        "pais_origen": "Brasil",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Brasil para evitar la doble tributacion",
        "fecha_firma": "1995-11-03",
        "fecha_vigencia": "1998-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1997-25678",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-ARG-001",
        "pais_origen": "Argentina",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Argentina para evitar la doble tributacion",
        "fecha_firma": "1990-11-16",
        "fecha_vigencia": "1993-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1992-28901",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-ITA-001",
        "pais_origen": "Italia",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana e Italia para evitar la doble tributacion",
        "fecha_firma": "1974-04-12",
        "fecha_vigencia": "1975-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1974-18901",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-PRT-001",
        "pais_origen": "Portugal",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Portugal para evitar la doble tributacion",
        "fecha_firma": "1969-11-22",
        "fecha_vigencia": "1970-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1969-15234",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
    {
        "codigo": "DTA-NLD-001",
        "pais_origen": "Paises Bajos",
        "pais_destino": "Espana",
        "titulo": "Convenio entre Espana y Paises Bajos para evitar la doble tributacion",
        "fecha_firma": "1984-03-14",
        "fecha_vigencia": "1985-01-01",
        "tipo_acuerdo": "bilateral",
        "boe_referencia": "BOE-A-1984-8901",
        "articulos": {"dividendos": "art.10", "intereses": "art.11", "royalties": "art.12"},
        "texto_completo": "Convenio para evitar la doble tributacion y prevenir la evasion fiscal en el ambito de los impuestos sobre la renta",
        "estado": "vigente",
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed irs_dta_convention")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in CONVENTIONS:
        d["articulos"] = json.dumps(d["articulos"])
        cur.execute(
            """INSERT INTO irs_dta_convention (codigo, pais_origen, pais_destino, titulo,
               fecha_firma, fecha_vigencia, tipo_acuerdo, boe_referencia,
               articulos, texto_completo, estado)
               VALUES (%(codigo)s, %(pais_origen)s, %(pais_destino)s, %(titulo)s,
                       %(fecha_firma)s, %(fecha_vigencia)s, %(tipo_acuerdo)s,
                       %(boe_referencia)s, %(articulos)s, %(texto_completo)s, %(estado)s)
               ON CONFLICT DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} irs_dta_convention records inserted")
    conn.close()


if __name__ == "__main__":
    main()
