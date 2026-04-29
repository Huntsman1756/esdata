import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

WITHHOLDING_RATES = [
    ("124", "Dividendos", 19.0, "Ley 29/1987, Art. 10", "BOE-A-1987-26900", True),
    ("124", "Intereses", 19.0, "Ley 29/1987, Art. 11", "BOE-A-1987-26900", True),
    ("124", "Regalias", 19.0, "Ley 29/1987, Art. 12", "BOE-A-1987-26900", True),
    ("124", "Rendimientos inmobiliarios", 24.0, "Ley 29/1987, Art. 13", "BOE-A-1987-26900", True),
    ("124", "Premios y loterías", 20.0, "Ley 29/1987, Art. 14", "BOE-A-1987-26900", True),
    ("124", "Renta por trabajo dependiente", 19.0, "Ley 29/1987, Art. 15", "BOE-A-1987-26900", True),
    ("212", "Dividendos (empresas)", 19.0, "Ley 29/1987, Art. 20", "BOE-A-1987-26900", True),
    ("212", "Intereses (empresas)", 19.0, "Ley 29/1987, Art. 21", "BOE-A-1987-26900", True),
    ("212", "Regalias (empresas)", 19.0, "Ley 29/1987, Art. 22", "BOE-A-1987-26900", True),
    ("116", "Actividades económicas", 24.0, "Ley 29/1987, Art. 44", "BOE-A-1987-26900", True),
    ("116", "Actividades económicas (DTA)", 15.0, "Convenio DTA — tipos reducidos", "BOE-A-2024-5000", True),
    ("123", "Rendimientos sin EP", 24.0, "Ley 29/1987, Art. 49", "BOE-A-1987-26900", True),
    ("123", "Rendimientos sin EP (DTA)", 15.0, "Convenio DTA — tipos reducidos", "BOE-A-2024-5000", True),
    ("216", "Facturas servicios", 24.0, "Ley 29/1987, Art. 20", "BOE-A-1987-26900", True),
    ("216", "Facturas servicios (DTA)", 15.0, "Convenio DTA — tipos reducidos", "BOE-A-2024-5000", True),
    ("296", "Resumen retenciones", 19.0, "Ley 29/1987, Art. 10-15", "BOE-A-1987-26900", True),
    ("878", "Relación proveedores", 24.0, "Ley 29/1987, Art. 30", "BOE-A-1987-26900", True),
]

INSTRUCCIONES = [
    ("124", "Seccion 1", "Autoliquidación de dividendos y rentas del capital mobiliario", "Instrucciones para el modelo 124: autoliquidación mensual de retenciones e pagos a cuenta sobre dividendos y rentas del capital mobiliario."),
    ("124", "Seccion 2", "Casillero por casillero", "Casillero 1: Importe bruto de dividendos. Casillero 2: Importe de la retención. Casillero 3: Total retenciones."),
    ("212", "Seccion 1", "Dividendos y rentas del capital mobiliario (empresas)", "Instrucciones para el modelo 212: autoliquidación mensual de retenciones sobre dividendos y rentas del capital mobiliario para empresas."),
    ("212", "Seccion 2", "Casillero por casillero", "Casillero 1: Dividendos distribuidos. Casillero 2: Retención practicada. Casillero 3: Tipo de retención aplicado."),
    ("116", "Seccion 1", "Actividades económicas (periodo trimestral)", "Instrucciones para el modelo 116: autoliquidación trimestral de actividades económicas de no residentes sin establecimiento permanente."),
    ("116", "Seccion 2", "Casillero por casillero", "Casillero 1: Rendimientos brutos. Casillero 2: Gastos deducibles. Casillero 3: Base imponible."),
    ("123", "Seccion 1", "Rendimientos sin establecimiento permanente", "Instrucciones para el modelo 123: autoliquidación de rendimientos sin establecimiento permanente."),
    ("216", "Seccion 1", "Facturas a terceros no residentes", "Instrucciones para el modelo 216: comunicación de facturas emitidas a terceros no residentes."),
    ("216", "Seccion 2", "Casillero por casillero", "Casillero 1: Facturas emitidas. Casillero 2: Importe bruto. Casillero 3: Retención aplicada."),
    ("296", "Seccion 1", "Resumen anual de retenciones", "Instrucciones para el modelo 296: resumen anual de retenciones e pagos a cuenta."),
    ("878", "Seccion 1", "Relación de pagos a proveedores no residentes", "Instrucciones para el modelo 878: comunicación anual de pagos a proveedores no residentes."),
]


def seed():
    import psycopg
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    for modelo_code, tipo_renta, tipo_retencion, articulo, fuente, activo in WITHHOLDING_RATES:
        cur.execute(
            """
            INSERT INTO irnr_withholding_rate (modelo_id, tipo_renta, tipo_retencion, articulo_referencia, fuente_texto, activo, creado_en, actualizado_en)
            VALUES ((SELECT id FROM aeat_modelo WHERE codigo = %s), %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """,
            (modelo_code, tipo_renta, tipo_retencion, articulo, fuente, activo),
        )

    for modelo_code, seccion, titulo, contenido in INSTRUCCIONES:
        cur.execute(
            """
            INSERT INTO irnr_instruccion (modelo_id, seccion, titulo, contenido, creado_en, actualizado_en)
            VALUES ((SELECT id FROM aeat_modelo WHERE codigo = %s), %s, %s, %s, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """,
            (modelo_code, seccion, titulo, contenido),
        )

    conn.commit()
    total = len(WITHHOLDING_RATES) + len(INSTRUCCIONES)
    print(f"Seeded {total} IRNR records ({len(WITHHOLDING_RATES)} rates + {len(INSTRUCCIONES)} instrucciones)")
    conn.close()


if __name__ == "__main__":
    seed()
