#!/usr/bin/env python
"""Seed de calendario fiscal con fechas reales 2025-2026."""

from datetime import datetime

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

CALENDARIO = [
    # Modelo 100 — IRPF 2025 (campana abril-junio 2026)
    {
        "codigo": "100",
        "campana": "2026",
        "fecha_inicio": "2026-04-02",
        "fecha_fin": "2026-06-30",
        "fecha_fin_prorroga": None,
        "observaciones": "Campana de Renta 2026 (ejercicio 2025). Con certificado digital: abril-junio. Sin certificado (con ayuda): abril-mayo.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/irpf/modelo_100_autoliquidacion_irpf.html",
    },
    # Modelo 303 — IVA trimestral 2025
    {
        "codigo": "303",
        "campana": "2025-T1",
        "fecha_inicio": "2025-04-01",
        "fecha_fin": "2025-04-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Primer trimestre 2025. Plazo: primeros 20 dias del mes siguiente.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_303_autoliquidacion_ivaversion_abreviada.html",
    },
    {
        "codigo": "303",
        "campana": "2025-T2",
        "fecha_inicio": "2025-07-01",
        "fecha_fin": "2025-07-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Segundo trimestre 2025.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_303_autoliquidacion_ivaversion_abreviada.html",
    },
    {
        "codigo": "303",
        "campana": "2025-T3",
        "fecha_inicio": "2025-10-01",
        "fecha_fin": "2025-10-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Tercer trimestre 2025.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_303_autoliquidacion_ivaversion_abreviada.html",
    },
    {
        "codigo": "303",
        "campana": "2025-T4",
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-01-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Cuarto trimestre 2025.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_303_autoliquidacion_ivaversion_abreviada.html",
    },
    # Modelo 200 — IS 2025
    {
        "codigo": "200",
        "campana": "2025",
        "fecha_inicio": "2026-04-01",
        "fecha_fin": "2026-06-30",
        "fecha_fin_prorroga": "2026-07-31",
        "observaciones": "Primeros 6 meses (hasta junio). Prorroga hasta julio si activo total > 10M€.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/is/modelo_200_autoliquidacion_impuesto_sociedades.html",
    },
    # Modelo 124 — IRNR dividendos 2025
    {
        "codigo": "124",
        "campana": "2025-01",
        "fecha_inicio": "2025-01-01",
        "fecha_fin": "2025-01-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Enero 2025. Periodo: mensual.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_124_autoliquidacion_retenciones_dividendos.html",
    },
    {
        "codigo": "124",
        "campana": "2025-02",
        "fecha_inicio": "2025-02-01",
        "fecha_fin": "2025-02-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Febrero 2025.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_124_autoliquidacion_retenciones_dividendos.html",
    },
    # Modelo 216 — FactA no residentes 2025
    {
        "codigo": "216",
        "campana": "2025-01",
        "fecha_inicio": "2025-01-01",
        "fecha_fin": "2025-01-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Enero 2025. Periodo: mensual.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_216_declaracion_facta.html",
    },
    {
        "codigo": "216",
        "campana": "2025-02",
        "fecha_inicio": "2025-02-01",
        "fecha_fin": "2025-02-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Febrero 2025.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/no_residentes/modelo_216_declaracion_facta.html",
    },
    # Modelo 349 — FactA intracomunitaria 2025
    {
        "codigo": "349",
        "campana": "2025-T1",
        "fecha_inicio": "2025-04-01",
        "fecha_fin": "2025-04-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Primer trimestre 2025. Se declara en el trimestre con datos mensuales.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_349_declaracion_operaciones_intracomunitarias.html",
    },
    # Modelo 347 — Operaciones terceros 2025
    {
        "codigo": "347",
        "campana": "2025",
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-03-31",
        "fecha_fin_prorroga": None,
        "observaciones": "Declaracion anual. Plazo: enero-marzo del ano siguiente.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_347_declaracion_operaciones_con_terceras_personas.html",
    },
    # Modelo 111 — Retribuciones 2025
    {
        "codigo": "111",
        "campana": "2025-01",
        "fecha_inicio": "2025-01-01",
        "fecha_fin": "2025-01-20",
        "fecha_fin_prorroga": None,
        "observaciones": "Enero 2025. Retenciones sobre retribuciones.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/retenciones/modelo_111_autoliquidacion_retribuciones_trabajadores.html",
    },
    # Modelo 394 — Resumen anual SII 2025
    {
        "codigo": "394",
        "campana": "2025",
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-02-28",
        "fecha_fin_prorroga": None,
        "observaciones": "Resumen anual de facturas del SII 2025. Plazo: enero-febrero 2026.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/iva/modelo_394_resumen_anual_sii.html",
    },
    # Modelo 720 — Bienes en extranjero 2025
    {
        "codigo": "720",
        "campana": "2025",
        "fecha_inicio": "2025-01-01",
        "fecha_fin": "2025-03-31",
        "fecha_fin_prorroga": None,
        "observaciones": "Declaracion trimestral durante el ano natural de adquisicion. Primer trimestre: enero-marzo.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/otros/modelo_720_informacion_bienes_extranjero.html",
    },
    # Modelo 190 — Remuneraciones totales 2025
    {
        "codigo": "190",
        "campana": "2025",
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-02-28",
        "fecha_fin_prorroga": None,
        "observaciones": "Relacion anual de retribuciones y pagos. Plazo: enero-febrero 2026.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/retenciones/modelo_190_retribuciones_anual.html",
    },
    # Modelo 430 — Exportaciones 2025
    {
        "codigo": "430",
        "campana": "2025-01",
        "fecha_inicio": "2025-01-01",
        "fecha_fin": "2025-01-10",
        "fecha_fin_prorroga": None,
        "observaciones": "Enero 2025. Listas operaciones de exportacion. Plazo: primeros 10 dias del mes siguiente.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/estadistica/modelo_430_listas_operaciones_comerciales.html",
    },
    # Modelo 431 — Importaciones 2025
    {
        "codigo": "431",
        "campana": "2025-01",
        "fecha_inicio": "2025-01-01",
        "fecha_fin": "2025-01-10",
        "fecha_fin_prorroga": None,
        "observaciones": "Enero 2025. Listas operaciones de importacion. Plazo: primeros 10 dias del mes siguiente.",
        "fuente": "https://www.sede.aeat.gob.es/Sede/enlectivo_hacienda/modelos-informacion-y-declaraciones/estadistica/modelo_431_listas_operaciones_comerciales.html",
    },
]


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    for entry in CALENDARIO:
        # Buscar modelo por codigo
        cur.execute("SELECT id FROM aeat_modelo WHERE codigo = %s", (entry["codigo"],))
        row = cur.fetchone()
        if not row:
            print(f"SKIP modelo {entry['codigo']}: no encontrado en DB")
            continue
        modelo_id = row[0]

        # Buscar campana por modelo_id y campana
        cur.execute(
            "SELECT id FROM modelo_campana WHERE modelo_id = %s AND campana = %s",
            (modelo_id, entry["campana"]),
        )
        camp_row = cur.fetchone()
        if not camp_row:
            print(f"SKIP campana {entry['campana']} para modelo {entry['codigo']}: no encontrada")
            continue
        campana_id = camp_row[0]

        # Insert calendario
        cur.execute(
            """INSERT INTO modelo_fiscal_calendar
               (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion,
                fecha_fin_prorroga, observaciones, fuente, activo)
                VALUES (%s, %s, %s, %s, %s, %s, true)
                ON CONFLICT DO NOTHING""",
            (
                campana_id,
                datetime.fromisoformat(entry["fecha_inicio"]),
                datetime.fromisoformat(entry["fecha_fin"]),
                datetime.fromisoformat(entry["fecha_fin_prorroga"]) if entry["fecha_fin_prorroga"] else None,
                entry["observaciones"],
                entry["fuente"],
            ),
        )

    conn.commit()
    print(f"OK: {len(CALENDARIO)} entradas de calendario fiscal seedeadas")
    conn.close()


if __name__ == "__main__":
    main()
