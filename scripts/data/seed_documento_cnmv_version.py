#!/usr/bin/env python3
"""Seed documento_cnmv_version — Versiones historicas de documentos CNMV.

Uso:
    python scripts/data/seed_documento_cnmv_version.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

CNMV_VERSIONS = [
    {
        "documento_referencia": "Guía 1/2023",
        "version_numero": 1,
        "estado_version": "draft",
        "fecha_version": datetime(2023, 1, 15).date(),
        "resumen_cambios": "Version inicial del borrador",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Guía 1/2023",
        "version_numero": 2,
        "estado_version": "published",
        "fecha_version": datetime(2023, 3, 1).date(),
        "resumen_cambios": "Ajustes tras consulta publica, incorporacion de comentarios sector",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Instruccion 2/2023",
        "version_numero": 1,
        "estado_version": "published",
        "fecha_version": datetime(2023, 5, 10).date(),
        "resumen_cambios": "Version inicial publicada",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Instruccion 2/2023",
        "version_numero": 2,
        "estado_version": "amended",
        "fecha_version": datetime(2023, 9, 20).date(),
        "resumen_cambios": "Modificacion de articulos 4 y 7 por actualizacion normativa",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Resolucion 3/2024",
        "version_numero": 1,
        "estado_version": "published",
        "fecha_version": datetime(2024, 1, 5).date(),
        "resumen_cambios": "Publicacion inicial",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Resolucion 3/2024",
        "version_numero": 2,
        "estado_version": "published",
        "fecha_version": datetime(2024, 6, 15).date(),
        "resumen_cambios": "Actualizacion de procedimientos de reporte",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Nota tecnica 4/2024",
        "version_numero": 1,
        "estado_version": "draft",
        "fecha_version": datetime(2024, 8, 1).date(),
        "resumen_cambios": "Borrador en consulta",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Acuerdo 5/2024",
        "version_numero": 1,
        "estado_version": "published",
        "fecha_version": datetime(2024, 10, 1).date(),
        "resumen_cambios": "Acuerdo del Consejo sobre criterios de aplicacion",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Guia 6/2024",
        "version_numero": 1,
        "estado_version": "published",
        "fecha_version": datetime(2024, 11, 15).date(),
        "resumen_cambios": "Guia sobre cumplimiento DAC8",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
    {
        "documento_referencia": "Guia 6/2024",
        "version_numero": 2,
        "estado_version": "amended",
        "fecha_version": datetime(2025, 1, 10).date(),
        "resumen_cambios": "Actualizacion por entrada en vigor de DAC8",
        "fuente_version": "Comision Nacional del Mercado de Valores",
        "creado_en": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed documento_cnmv_version")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in CNMV_VERSIONS:
        cur.execute(
            """INSERT INTO documento_cnmv_version (documento_referencia, version_numero,
               estado_version, fecha_version, resumen_cambios, fuente_version, creado_en)
               VALUES (%(documento_referencia)s, %(version_numero)s, %(estado_version)s,
                       %(fecha_version)s, %(resumen_cambios)s, %(fuente_version)s,
                       %(creado_en)s)
               ON CONFLICT (documento_referencia, version_numero) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} documento_cnmv_version records inserted")
    conn.close()


if __name__ == "__main__":
    main()
