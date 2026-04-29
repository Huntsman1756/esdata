#!/usr/bin/env python3
"""Seed irs_withholding_rule — Reglas de retencion fiscal por tipo de renta.

Uso:
    python scripts/data/seed_irs_withholding_rule.py [--database-url URL]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

WITHHOLDING_RULES = [
    {
        "codigo": "WTH_DIVIDEND",
        "tipo_renta": "dividend",
        "tipo_renta_espanol": "Dividendos",
        "tipo_retencion_default": 19.0,
        "tipo_retencion_dta": 10.0,
        "pais_aplicable": None,
        "descripcion": "Retencion standard sobre dividendos para no residentes",
        "norma_referencia": "TRLIS",
        "articulo_referencia": "Art. 64",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_INTEREST",
        "tipo_renta": "interest",
        "tipo_renta_espanol": "Intereses",
        "tipo_retencion_default": 19.0,
        "tipo_retencion_dta": 10.0,
        "pais_aplicable": None,
        "descripcion": "Retencion standard sobre intereses para no residentes",
        "norma_referencia": "TRLIS",
        "articulo_referencia": "Art. 64",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_ROYALTY",
        "tipo_renta": "royalty",
        "tipo_renta_espanol": "Regalias",
        "tipo_retencion_default": 19.0,
        "tipo_retencion_dta": 5.0,
        "pais_aplicable": None,
        "descripcion": "Retencion sobre regalias y derechos de propiedad intelectual",
        "norma_referencia": "TRLIS",
        "articulo_referencia": "Art. 64",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_CAP_GAIN",
        "tipo_renta": "capital_gain",
        "tipo_renta_espanol": "Ganancias patrimoniales",
        "tipo_retencion_default": 19.0,
        "tipo_retencion_dta": None,
        "pais_aplicable": None,
        "descripcion": "Retencion sobre ganancias patrimoniales por transmision de activos",
        "norma_referencia": "TRLIS",
        "articulo_referencia": "Art. 64",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_SERVICES",
        "tipo_renta": "services",
        "tipo_renta_espanol": "Servicios",
        "tipo_retencion_default": 19.0,
        "tipo_retencion_dta": 15.0,
        "pais_aplicable": None,
        "descripcion": "Retencion sobre pagos de servicios al extranjero",
        "norma_referencia": "TRLIS",
        "articulo_referencia": "Art. 64",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_CONSTRUCTION",
        "tipo_renta": "construction",
        "tipo_renta_espanol": "Construcción",
        "tipo_retencion_default": 19.0,
        "tipo_retencion_dta": 15.0,
        "pais_aplicable": None,
        "descripcion": "Retencion sobre obras de construccion en territorio espanol",
        "norma_referencia": "TRLIS",
        "articulo_referencia": "Art. 64",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_PENSION",
        "tipo_renta": "pension",
        "tipo_renta_espanol": "Pensiones",
        "tipo_retencion_default": 19.0,
        "tipo_retencion_dta": 10.0,
        "pais_aplicable": None,
        "descripcion": "Retencion sobre pensiones pagadas a residentes en el extranjero",
        "norma_referencia": "TRLIS",
        "articulo_referencia": "Art. 64",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_LOTTERY",
        "tipo_renta": "lottery",
        "tipo_renta_espanol": "Premios",
        "tipo_retencion_default": 20.0,
        "tipo_retencion_dta": None,
        "pais_aplicable": None,
        "descripcion": "Retencion sobre premios y loterias para no residentes",
        "norma_referencia": "LIRPF",
        "articulo_referencia": "Art. 56",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_INDIVIDUAL",
        "tipo_renta": "individual",
        "tipo_renta_espanol": "Renta individual no residente",
        "tipo_retencion_default": 24.0,
        "tipo_retencion_dta": None,
        "pais_aplicable": None,
        "descripcion": "Tipo general de retencion para no residentes en IRNR",
        "norma_referencia": "LRNR",
        "articulo_referencia": "Art. 44",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
    {
        "codigo": "WTH_EU_PARENT",
        "tipo_renta": "dividend",
        "tipo_renta_espanol": "Dividendos directiva matriz-filial",
        "tipo_retencion_default": 0.0,
        "tipo_retencion_dta": None,
        "pais_aplicable": "EU",
        "descripcion": "Retencion 0% sobre dividendos bajo Directiva Matriz-Filial",
        "norma_referencia": "2014/86/UE",
        "articulo_referencia": "Art. 4",
        "estado": "active",
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed irs_withholding_rule")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in WITHHOLDING_RULES:
        cur.execute(
            """INSERT INTO irs_withholding_rule (codigo, tipo_renta, tipo_renta_espanol,
               tipo_retencion_default, tipo_retencion_dta, pais_aplicable, descripcion,
               norma_referencia, articulo_referencia, estado, creado_en, actualizado_en)
               VALUES (%(codigo)s, %(tipo_renta)s, %(tipo_renta_espanol)s,
                       %(tipo_retencion_default)s, %(tipo_retencion_dta)s, %(pais_aplicable)s,
                       %(descripcion)s, %(norma_referencia)s, %(articulo_referencia)s,
                       %(estado)s, %(creado_en)s, %(actualizado_en)s)
               ON CONFLICT DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} irs_withholding_rule records inserted")
    conn.close()


if __name__ == "__main__":
    main()
