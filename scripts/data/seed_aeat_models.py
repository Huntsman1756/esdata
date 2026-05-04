#!/usr/bin/env python
"""LEGACY / NO AUTORITATIVO.

Seed de modelos AEAT — extension del seed_modelos.py existente.

Crea modelos AEAT adicionales en la tabla aeat_modelo (codigo text).
Los modelos existentes en seed_modelos.py ya cubren los principales.
Este seed añade modelos complementarios para cobertura completa.

No usar como flujo canonico productivo AEAT. La via canonica del repo MCP es:
1. `python scripts/seed-modelos.py --db-url <DATABASE_URL>`
2. `python scripts/seed-modelos-v2.py --db-url <DATABASE_URL> --campana <YEAR>`

Uso:
    python scripts/data/seed_aeat_models.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

MODELOS = [
    ("051", "Autoliquidacion de tasas y precios publicos", "variable", "tasa", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/tasas/modelo_051_autoliquidacion_tasas_precios_publicos.html"),
    ("056", "Pago fraccionado de operaciones con bienes inmuebles", "variable", "impuesto_real", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_056_pago_fraccionado.html"),
    ("083", "Autoliquidacion de tasas y precios publicos (no voluntario)", "variable", "tasa", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/tasas/modelo_083_autoliquidacion_tasas.html"),
    ("131", "IRPF — Estimacion directa simplificada (cuotas trimestrales)", "trimestral", "IRPF", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/irpf/modelo_131_autoliquidacion_cuotas_trimestrales.html"),
    ("136", "Actividades economicas — Ingresos y pagos realizados por terceros", "anual", "IRPF", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_136_ingresos_pagos_terceros.html"),
    ("138", "Dividendos y participationes en entidades", "anual", "IRPF", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/retenciones/modelo_138_dividendos_participationes.html"),
    ("202", "Liquidacion anual IRPF (cuotas trimestrales)", "trimestral", "IRPF", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/irpf/modelo_202_liquidacion_anual_cuotas_trimestrales.html"),
    ("207", "Entidades no residentes en Espana", "trimestral", "IRNR", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_207_entidades_no_residentes.html"),
    ("216", "IRNR — FactA a terceros (no residentes)", "mensual", "IRNR", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_216_declaracion_facta.html"),
    ("252", "Datos de elementos patrimoniales adquiridos y enajenados", "anual", "IRPF", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_252_elementos_patrimoniales.html"),
    ("309", "Cuotas a cuenta del ITPAJD", "mensual", "ITPAJD", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_309_cuotas_a_cuenta.html"),
    ("340", "Operaciones con bienes de inversion", "trimestral", "IVA", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_340_bienes_inversion.html"),
    ("415", "Registro facturas expedidas (SII)", "trimestral", "IVA", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_415_registro_facturas_expedidas.html"),
    ("416", "Registro facturas recibidas (SII)", "trimestral", "IVA", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_416_registro_facturas_recibidas.html"),
    ("419", "Resumenes trimestrales de facturas expedidas y recibidas", "trimestral", "IVA", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_419_resumenes_trimestrales.html"),
    ("420", "Informacion sobre operaciones con partes vinculadas", "anual", "IS", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_420_partes_vinculadas.html"),
    ("424", "Informacion sobre actividades economicas", "anual", "estadistico", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/estadistica/modelo_424_actividades_economicas.html"),
    ("610", "Comunicacion de operaciones intracomunitarias de bienes y servicios", "trimestral", "IVA", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_610_operaciones_intracomunitarias.html"),
    ("636", "Declaracion resumen de adquisiciones intracomunitarias", "trimestral", "IVA", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_636_resumen_adquisiciones.html"),
    ("645", "Comunicacion de datos de planes y seguros de pensiones", "anual", "IRPF", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/pensiones/modelo_645_planes_seguros_pensiones.html"),
    ("750", "Declaracion de bienes en el extranjero", "anual", "informacion", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_750_bienes_extranjero.html"),
    ("848", "Operaciones con activos financieros", "trimestral", "IRPF", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/retenciones/modelo_848_operaciones_activos_financieros.html"),
    ("290", "Comunicacion de datos de operaciones con partes vinculadas", "trimestral", "IS", "https://www.sede.agenciatributaria.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_290_datos_operaciones_vinculadas.html"),
]


def main():
    parser = argparse.ArgumentParser(description="Seed AEAT modelos adicionales")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    inserted = 0
    for codigo, nombre, periodo, impuesto, url_info in MODELOS:
        cur.execute(
            """INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET
                   nombre = EXCLUDED.nombre,
                   periodo = EXCLUDED.periodo,
                   impuesto = EXCLUDED.impuesto,
                   url_info = EXCLUDED.url_info
               WHERE aeat_modelo.nombre != EXCLUDED.nombre
                  OR aeat_modelo.periodo != EXCLUDED.periodo
                  OR aeat_modelo.impuesto != EXCLUDED.impuesto
                  OR aeat_modelo.url_info != EXCLUDED.url_info""",
            (codigo, nombre, periodo, impuesto, url_info),
        )
        inserted += 1

    conn.commit()
    print(f"OK: {inserted} modelos AEAT insertados/actualizados")
    conn.close()


if __name__ == "__main__":
    main()
