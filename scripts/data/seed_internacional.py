#!/usr/bin/env python3
"""Seed de obligaciones internacionales (FATCA, CRS, IGA, DAC6-8).

Fuente: OCDE, UE, leyes espanolas de implementacion.
verified_date: 2026-04-29

Uso:
    python scripts/data/seed_internacional.py
    python scripts/data/seed_internacional.py --db-url postgresql://user:pass@host:5432/db
"""

import argparse
import os
import psycopg

DB_URL_DEFAULT = os.getenv(
    "DATABASE_URL",
    "postgresql://esdata:esdata_dev@localhost:5432/esdata",
)

OBLIGACIONES = [
    (
        "FATCA",
        "Foreign Account Tax Compliance Act (FATCA) — Ley 16/2012 de implementacion",
        "ley",
        "US",
        "ES",
        "2012-12-28",
        None,
        "Ley espanola que implementa FATCA en Espana, requiriendo a instituciones financieras espanolas reportar cuentas de titulares estadounidenses al IRS.",
    ),
    (
        "CRS",
        "Common Reporting Standard (CRS) — Estandar OCDE para intercambio automatico de informacion financiera",
        "estandar",
        "OCDE",
        "internacional",
        "2016-01-01",
        None,
        "Estandar internacional para el intercambio automatico de informacion financiera entre jurisdicciones participantes para combatir la evasione fiscal transfronteriza.",
    ),
    (
        "FATCA_IGA_ES",
        "Acuerdo Intergubernamental FATCA entre Espana y Estados Unidos — Modelo 1",
        "convenio",
        "ES-US",
        "ES-US",
        "2013-09-02",
        None,
        "Acuerdo intergubernamental Modelo 1 entre Espana y EE.UU. para la implementacion de FATCA. Espana intercambia informacion automaticamente con el IRS.",
    ),
    (
        "DAC6",
        "Directiva DAC6 — Reporte obligatorio de arreglos transfronterizos agresivos",
        "directiva",
        "UE",
        "UE",
        "2018-06-25",
        None,
        "Obliga a intermediarios a reportar arreglos transfronterizos que cumplan hallmarks de agresividad fiscal.",
    ),
    (
        "DAC7",
        "Directiva DAC7 — Informacion para plataformas digitales",
        "directiva",
        "UE",
        "UE",
        "2020-12-22",
        None,
        "Requiere que las plataformas digitales reporten informacion sobre los vendedores que utilizan sus servicios.",
    ),
    (
        "DAC8",
        "Directiva DAC8 — Informacion sobre criptoactivos",
        "directiva",
        "UE",
        "UE",
        "2023-12-27",
        None,
        "Extiende el intercambio automatico de informacion para incluir criptoactivos y cripto-proveedores de servicios.",
    ),
]


def main(db_url: str | None = None):
    conn = psycopg.connect(db_url or DB_URL_DEFAULT)
    cur = conn.cursor()

    for codigo, titulo, tipo, origen, aplicacion, vigente_desde, vigente_hasta, descripcion in OBLIGACIONES:
        cur.execute(
            """
            INSERT INTO obligacion_internacional
                (codigo, titulo, tipo, jurisdiccion_origen, jurisdiccion_aplicacion,
                 vigente_desde, vigente_hasta, descripcion, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'activo')
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                tipo = EXCLUDED.tipo,
                descripcion = EXCLUDED.descripcion,
                actualizado_en = now()
            """,
            (codigo, titulo, tipo, origen, aplicacion, vigente_desde, vigente_hasta, descripcion),
        )

    conn.commit()
    print(f"Seed completado: {len(OBLIGACIONES)} obligaciones internacionales")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed international obligations (FATCA, CRS, DAC)")
    parser.add_argument(
        "--db-url",
        default=None,
        help="Database URL (default: $DATABASE_URL or postgresql://esdata:esdata_dev@localhost:5432/esdata)",
    )
    args = parser.parse_args()
    main(args.db_url)
