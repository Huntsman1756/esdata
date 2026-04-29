#!/usr/bin/env python3
"""Seed irs_fiscal_norma — Normas fiscales para IRS (Impuesto de Sociedades).

Uso:
    python scripts/data/seed_irs_fiscal_norma.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

NORMAS = [
    {
        "codigo": "LIS-001",
        "titulo": "Impuesto sobre Sociedades — Ley 27/2014",
        "tipo": "ley",
        "anio_vigencia": 2014,
        "texto": "Ley 27/2014, de 27 de noviembre, del Impuesto sobre Sociedades",
        "url_fuente": "https://www.boe.es/eli/es/l/2014-11-27/27",
        "estado": "activo",
    },
    {
        "codigo": "LIS-002",
        "titulo": "Reglamento LIS — RD 1777/2004",
        "tipo": "reglamento",
        "anio_vigencia": 2004,
        "texto": "Real Decreto 1777/2004, de 30 de julio, por el que se aprueba el Reglamento del Impuesto sobre Sociedades",
        "url_fuente": "https://www.boe.es/eli/es/rd/2004-07-30/1777",
        "estado": "activo",
    },
    {
        "codigo": "LIS-003",
        "titulo": "Reglamento LIS grandes empresas — RD 1777/2004 art. 126",
        "tipo": "reglamento",
        "anio_vigencia": 2004,
        "texto": "Disposiciones especiales para grandes empresas en el Reglamento del Impuesto sobre Sociedades",
        "url_fuente": "https://www.boe.es/eli/es/rd/2004-07-30/1777",
        "estado": "activo",
    },
    {
        "codigo": "RD-1002-2025",
        "titulo": "RD 1002/2025 — Plan de cuentas para grupos de empresas",
        "tipo": "reglamento",
        "anio_vigencia": 2025,
        "texto": "Real Decreto 1002/2025 por el que se aprueba el plan de cuentas anual para grupos de empresas",
        "url_fuente": "https://www.boe.es/eli/es/rd/2025-01-01/1002",
        "estado": "activo",
    },
    {
        "codigo": "DGT-V1140-24",
        "titulo": "Consulta DGT V1140-24 — ESOP y tratamiento fiscal",
        "tipo": "publicacion",
        "anio_vigencia": 2024,
        "texto": "Consulta DGT V1140-24 sobre tratamiento fiscal de opciones de compra de acciones para empleados",
        "url_fuente": "https://sede.agenciatributaria.gob.es/Sede/en_tramite/consultas/resoluciones.html",
        "estado": "activo",
    },
    {
        "codigo": "DGT-V2223-22",
        "titulo": "Consulta DGT V2223-22 — Doble imposicion internacional",
        "tipo": "publicacion",
        "anio_vigencia": 2022,
        "texto": "Consulta DGT V2223-22 sobre deducción por doble imposicion internacional en el Impuesto sobre Sociedades",
        "url_fuente": "https://sede.agenciatributaria.gob.es/Sede/en_tramite/consultas/resoluciones.html",
        "estado": "activo",
    },
    {
        "codigo": "DGT-V1902-23",
        "titulo": "Consulta DGT V1902-23 — Deduccion I+D+i",
        "tipo": "publicacion",
        "anio_vigencia": 2023,
        "texto": "Consulta DGT V1902-23 sobre deducción por actividades de I+D+i en el Impuesto sobre Sociedades",
        "url_fuente": "https://sede.agenciatributaria.gob.es/Sede/en_tramite/consultas/resoluciones.html",
        "estado": "activo",
    },
    {
        "codigo": "RD-435-2025",
        "titulo": "RD 435/2025 — Modificacion tipo LIS",
        "tipo": "reglamento",
        "anio_vigencia": 2025,
        "texto": "Real Decreto 435/2025 por el que se modifica el tipo general del Impuesto sobre Sociedades",
        "url_fuente": "https://www.boe.es/eli/es/rd/2025-01-01/435",
        "estado": "activo",
    },
    {
        "codigo": "DGT-2025-001",
        "titulo": "Instruccion DGT 1/2025 — Normas de valoracion",
        "tipo": "publicacion",
        "anio_vigencia": 2025,
        "texto": "Instruccion de la DGT 1/2025 sobre normas de valoracion para el Impuesto sobre Sociedades",
        "url_fuente": "https://sede.agenciatributaria.gob.es/Sede/en_tramite/consultas/resoluciones.html",
        "estado": "activo",
    },
    {
        "codigo": "RD-1619-2012",
        "titulo": "RD 1619/2012 — Reglamento del LIS",
        "tipo": "reglamento",
        "anio_vigencia": 2012,
        "texto": "Real Decreto 1619/2012 por el que se aprueba el Reglamento del Impuesto sobre Sociedades para pequenas empresas",
        "url_fuente": "https://www.boe.es/eli/es/rd/2012-11-10/1619",
        "estado": "activo",
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed irs_fiscal_norma")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in NORMAS:
        cur.execute(
            """INSERT INTO irs_fiscal_norma (codigo, titulo, tipo, anio_vigencia,
               texto, url_fuente, estado)
               VALUES (%(codigo)s, %(titulo)s, %(tipo)s, %(anio_vigencia)s,
                       %(texto)s, %(url_fuente)s, %(estado)s)
               ON CONFLICT DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} irs_fiscal_norma records inserted")
    conn.close()


if __name__ == "__main__":
    main()
