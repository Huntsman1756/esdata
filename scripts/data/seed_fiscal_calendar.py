#!/usr/bin/env python
"""Seed calendario fiscal 2026 — plazos presentacion modelos AEAT.

Fuente: AEAT Calendario del Contribuyente 2026
verified_date: 2026-04-12
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

CALENDARIO = [
    # Enero 2026
    ("2026", "111", "2026-01-01", "2026-01-20", "Retenciones e ingresos a cuenta rendimientos trabajo y actividades economicas, Q4 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Enero, hasta el 20"),
    ("2026", "115", "2026-01-01", "2026-01-20", "Retenciones e ingresos a cuenta rentas arrendamiento inmuebles urbanos, Q4 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Enero, hasta el 20"),
    ("2026", "123", "2026-01-01", "2026-01-20", "Retenciones e ingresos a cuenta rendimientos capital mobiliario, Q4 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Enero, hasta el 20"),
    ("2026", "130", "2026-01-01", "2026-01-30", "IRPF pago fraccionado estimacion directa empresarios profesionales, Q4 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Enero, hasta el 30"),
    ("2026", "131", "2026-01-01", "2026-01-30", "IRPF pago fraccionado estimacion objetiva modulos, Q4 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Enero, hasta el 30"),
    ("2026", "303", "2026-01-01", "2026-01-30", "IVA autoliquidacion, Q4 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Enero, hasta el 30"),
    ("2026", "349", "2026-01-01", "2026-01-30", "IVA declaracion recapitulativa operaciones intracomunitarias, Q4 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Enero, hasta el 30"),
    ("2026", "390", "2026-01-01", "2026-01-30", "IVA declaracion resumen anual 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Enero, hasta el 30"),
    # Febrero 2026
    ("2026", "180", "2026-02-01", "2026-02-02", "Retenciones arrendamientos inmuebles urbanos resumen anual 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Febrero, hasta el 2"),
    ("2026", "190", "2026-02-01", "2026-02-02", "Retenciones e ingresos a cuenta rendimientos trabajo y actividades economicas resumen anual 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Febrero, hasta el 2"),
    ("2026", "193", "2026-02-01", "2026-02-02", "Retenciones e ingresos a cuenta capital mobiliario resumen anual 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Febrero, hasta el 2"),
    ("2026", "184", "2026-02-01", "2026-02-02", "Declaracion informativa entidades regimen atribucion de rentas anual 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Febrero, hasta el 2"),
    ("2026", "345", "2026-02-01", "2026-02-02", "Declaracion informativa planes de pensiones y sistemas alternativos anual 2025", "todos", "AEAT Calendario Contribuyente 2026 — Febrero, hasta el 2"),
    ("2026", "182", "2026-02-01", "2026-02-02", "Declaracion informativa donativos donaciones aportaciones recibidas anual 2025", "todos", "AEAT Calendario Contribuyente 2026 — Febrero, hasta el 2"),
    # Marzo 2026
    ("2026", "347", "2026-03-01", "2026-03-02", "Declaracion anual operaciones con terceras personas ejercicio 2025", "autonomos", "AEAT Calendario Contribuyente 2026 — Marzo, hasta el 2"),
    ("2026", "720", "2026-03-01", "2026-03-31", "Declaracion informativa bienes y derechos situados en extranjero ejercicio 2025", "todos", "AEAT Calendario Contribuyente 2026 — Marzo, hasta el 31"),
    ("2026", "721", "2026-03-01", "2026-03-31", "Declaracion informativa monedas virtuales situadas en extranjero ejercicio 2025", "todos", "AEAT Calendario Contribuyente 2026 — Marzo, hasta el 31"),
    # Abril 2026
    ("2026", "111", "2026-04-01", "2026-04-20", "Retenciones e ingresos a cuenta rendimientos trabajo y actividades economicas, Q1 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Abril, hasta el 20"),
    ("2026", "115", "2026-04-01", "2026-04-20", "Retenciones e ingresos a cuenta arrendamientos inmuebles urbanos, Q1 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Abril, hasta el 20"),
    ("2026", "123", "2026-04-01", "2026-04-20", "Retenciones e ingresos a cuenta capital mobiliario, Q1 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Abril, hasta el 20"),
    ("2026", "130", "2026-04-01", "2026-04-20", "IRPF pago fraccionado estimacion directa, Q1 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Abril, hasta el 20"),
    ("2026", "131", "2026-04-01", "2026-04-20", "IRPF pago fraccionado estimacion objetiva modulos, Q1 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Abril, hasta el 20"),
    ("2026", "303", "2026-04-01", "2026-04-20", "IVA autoliquidacion, Q1 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Abril, hasta el 20"),
    ("2026", "349", "2026-04-01", "2026-04-20", "IVA declaracion recapitulativa operaciones intracomunitarias, Q1 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Abril, hasta el 20"),
    ("2026", "202", "2026-04-01", "2026-04-20", "Impuesto sobre Sociedades pago fraccionado regimen general", "sociedades", "AEAT Calendario Contribuyente 2026 — Abril, hasta el 20"),
    # Renta 2026 (ejercicio 2025)
    ("2026", "100", "2026-04-08", "2026-06-30", "IRPF declaracion anual Renta 2025 presentacion por Internet", "todos", "AEAT Calendario Contribuyente 2026 — Campana Renta y Patrimonio"),
    ("2026", "714", "2026-04-08", "2026-06-30", "Impuesto sobre Patrimonio declaracion anual 2025", "todos", "AEAT Calendario Contribuyente 2026 — Campana Renta y Patrimonio"),
    ("2026", "100", "2026-04-08", "2026-06-25", "IRPF declaracion anual Renta 2025 resultado a ingresar con domiciliacion en cuenta", "todos", "AEAT Calendario Contribuyente 2026 — Junio, hasta el 25"),
    ("2026", "714", "2026-04-08", "2026-06-25", "Impuesto sobre Patrimonio 2025 resultado a ingresar con domiciliacion en cuenta", "todos", "AEAT Calendario Contribuyente 2026 — Junio, hasta el 25"),
    ("2026", "100", "2026-05-06", "2026-06-30", "IRPF declaracion anual Renta 2025 confeccion por telefono (cita previa desde 29 abril)", "todos", "AEAT Calendario Contribuyente 2026 — Campana Renta y Patrimonio"),
    ("2026", "100", "2026-06-01", "2026-06-30", "IRPF declaracion anual Renta 2025 atencion presencial en oficinas (cita previa desde 29 mayo)", "todos", "AEAT Calendario Contribuyente 2026 — Campana Renta y Patrimonio"),
    # Julio 2026
    ("2026", "111", "2026-07-01", "2026-07-20", "Retenciones e ingresos a cuenta rendimientos trabajo y actividades economicas, Q2 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 20"),
    ("2026", "115", "2026-07-01", "2026-07-20", "Retenciones e ingresos a cuenta arrendamientos inmuebles urbanos, Q2 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 20"),
    ("2026", "123", "2026-07-01", "2026-07-20", "Retenciones e ingresos a cuenta capital mobiliario, Q2 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 20"),
    ("2026", "130", "2026-07-01", "2026-07-20", "IRPF pago fraccionado estimacion directa, Q2 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 20"),
    ("2026", "131", "2026-07-01", "2026-07-20", "IRPF pago fraccionado estimacion objetiva modulos, Q2 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 20"),
    ("2026", "303", "2026-07-01", "2026-07-20", "IVA autoliquidacion, Q2 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 20"),
    ("2026", "349", "2026-07-01", "2026-07-20", "IVA declaracion recapitulativa operaciones intracomunitarias, Q2 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 20"),
    ("2026", "200", "2026-07-01", "2026-07-27", "Impuesto sobre Sociedades declaracion anual 2025 ejercicio coincidente ano natural", "sociedades", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 27"),
    ("2026", "718", "2026-07-01", "2026-07-31", "Impuesto Temporal Solidaridad Grandes Fortunas declaracion anual 2025", "todos", "AEAT Calendario Contribuyente 2026 — Julio, hasta el 31"),
    # Octubre 2026
    ("2026", "111", "2026-10-01", "2026-10-20", "Retenciones e ingresos a cuenta rendimientos trabajo y actividades economicas, Q3 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Octubre, hasta el 20"),
    ("2026", "115", "2026-10-01", "2026-10-20", "Retenciones e ingresos a cuenta arrendamientos inmuebles urbanos, Q3 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Octubre, hasta el 20"),
    ("2026", "123", "2026-10-01", "2026-10-20", "Retenciones e ingresos a cuenta capital mobiliario, Q3 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Octubre, hasta el 20"),
    ("2026", "130", "2026-10-01", "2026-10-20", "IRPF pago fraccionado estimacion directa, Q3 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Octubre, hasta el 20"),
    ("2026", "131", "2026-10-01", "2026-10-20", "IRPF pago fraccionado estimacion objetiva modulos, Q3 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Octubre, hasta el 20"),
    ("2026", "303", "2026-10-01", "2026-10-20", "IVA autoliquidacion, Q3 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Octubre, hasta el 20"),
    ("2026", "349", "2026-10-01", "2026-10-20", "IVA declaracion recapitulativa operaciones intracomunitarias, Q3 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Octubre, hasta el 20"),
    ("2026", "202", "2026-10-01", "2026-10-20", "Impuesto sobre Sociedades pago fraccionado regimen general octubre", "sociedades", "AEAT Calendario Contribuyente 2026 — Octubre, hasta el 20"),
    # Noviembre 2026
    ("2026", "102", "2026-11-01", "2026-11-05", "IRPF segundo plazo declaracion anual Renta 2025 si se fracciono el pago", "todos", "AEAT Calendario Contribuyente 2026 — Noviembre, hasta el 5"),
    # Diciembre 2026
    ("2026", "111", "2026-12-01", "2026-12-21", "Retenciones e ingresos a cuenta rendimientos trabajo y actividades economicas noviembre 2026 grandes empresas mensual", "autonomos", "AEAT Calendario Contribuyente 2026 — Diciembre, hasta el 21"),
    ("2026", "115", "2026-12-01", "2026-12-21", "Retenciones e ingresos a cuenta arrendamientos inmuebles urbanos noviembre 2026 grandes empresas mensual", "autonomos", "AEAT Calendario Contribuyente 2026 — Diciembre, hasta el 21"),
    ("2026", "202", "2026-12-01", "2026-12-21", "Impuesto sobre Sociedades pago fraccionado regimen general diciembre", "sociedades", "AEAT Calendario Contribuyente 2026 — Diciembre, hasta el 21"),
    ("2026", "349", "2026-12-01", "2026-12-21", "IVA declaracion recapitulativa operaciones intracomunitarias noviembre 2026", "autonomos", "AEAT Calendario Contribuyente 2026 — Diciembre, hasta el 21"),
]


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    count = 0
    for row in CALENDARIO:
        cur.execute(
            """INSERT INTO fiscal_calendar (year, modelo_codigo, date_start, date_end,
               description, who_applies, source)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (year, modelo_codigo, date_start, date_end)
               DO UPDATE SET
                   description = EXCLUDED.description,
                   who_applies = EXCLUDED.who_applies,
                   source = EXCLUDED.source""",
            row,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} plazos de calendario fiscal 2026 insertados")
    conn.close()


if __name__ == "__main__":
    main()
