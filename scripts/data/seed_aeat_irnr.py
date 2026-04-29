#!/usr/bin/env python3
"""Seed IRNR models — Modelos AEAT de no residentes.

Crea modelos IRNR (116, 123, 124, 212, 216, 296, 878) con metadatos
de periodo e impuestos. Basado en el worker aeat_irnr.py.

Uso:
    python scripts/data/seed_aeat_irnr.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

IRNR_MODELOS = [
    {
        "codigo": "116",
        "nombre": "Actividades economicas (periodo trimestral)",
        "periodo": "trimestral",
        "impuesto": "IRNR",
        "url_info": "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_116_autoliquidacion_actividades_economicas.html",
    },
    {
        "codigo": "123",
        "nombre": "Rendimientos sin establecimiento permanente",
        "periodo": "trimestral",
        "impuesto": "IRNR",
        "url_info": "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_123_autoliquidacion_rendimientos_sin_residente.html",
    },
    {
        "codigo": "124",
        "nombre": "Dividendos y rentas del capital mobiliario",
        "periodo": "mensual",
        "impuesto": "IRNR",
        "url_info": "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_124_autoliquidacion_retenciones_dividendos.html",
    },
    {
        "codigo": "212",
        "nombre": "Dividendos y rentas del capital (empresas)",
        "periodo": "mensual",
        "impuesto": "IRNR",
        "url_info": "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_212_autoliquidacion_dividendos_rentas_capital.html",
    },
    {
        "codigo": "216",
        "nombre": "FactA a terceros (no residentes)",
        "periodo": "mensual",
        "impuesto": "IRNR",
        "url_info": "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_216_declaracion_facta.html",
    },
    {
        "codigo": "296",
        "nombre": "Resumen anual de retenciones",
        "periodo": "mensual",
        "impuesto": "IRNR",
        "url_info": "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_296_autoliquidacion_intereses_canones.html",
    },
    {
        "codigo": "878",
        "nombre": "Relacion de pagos a proveedores no residentes",
        "periodo": "anual",
        "impuesto": "IRNR",
        "url_info": "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_878_relacion_pagos_proveedores.html",
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed IRNR models")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    for m in IRNR_MODELOS:
        cur.execute(
            """INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
               VALUES (%(codigo)s, %(nombre)s, %(periodo)s, %(impuesto)s, %(url_info)s)
               ON CONFLICT (codigo) DO UPDATE SET
                   nombre = EXCLUDED.nombre,
                   periodo = COALESCE(EXCLUDED.periodo, aeat_modelo.periodo),
                   impuesto = COALESCE(EXCLUDED.impuesto, aeat_modelo.impuesto),
                   url_info = EXCLUDED.url_info
               WHERE aeat_modelo.nombre != EXCLUDED.nombre
                  OR aeat_modelo.periodo != EXCLUDED.periodo
                  OR aeat_modelo.impuesto != EXCLUDED.impuesto
                  OR aeat_modelo.url_info != EXCLUDED.url_info""",
            m,
        )

    conn.commit()
    print(f"OK: {len(IRNR_MODELOS)} modelos IRNR insertados ({', '.join(m['codigo'] for m in IRNR_MODELOS)})")
    conn.close()


if __name__ == "__main__":
    main()
