import os
import uuid

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

NORMAS = [
    ("NV1", "Norma de Valoración 1ª — Fondos propios", "norma_valoracion", "Las participaciones en participaciones y en instrumentos de patrimonio de otras entidades se valorarán por su valor de realización estimado, deduciendo, en su caso, las estimaciones de pérdidas."),
    ("NV2", "Norma de Valoración 2ª — Inmovilizado material", "norma_valoracion", "El inmovilizado material se valorará por su valor de adquisición o producción, deduciendo las pérdidas por deterioro y las amortizaciones acumuladas."),
    ("NV3", "Norma de Valoración 3ª — Inmovilizado inmaterial", "norma_valoracion", "El inmovilizado inmaterial se valorará por su valor de adquisición o producción, deduciendo las pérdidas por deterioro y las amortizaciones acumuladas."),
    ("NV4", "Norma de Valoración 4ª — Inversiones financieras", "norma_valoracion", "Las inversiones financieras se valorarán por su valor de realización estimado, deduciendo las pérdidas por deterioro."),
    ("NV5", "Norma de Valoración 5ª — Existencias", "norma_valoracion", "Las existencias se valorarán por su coste de adquisición o producción, o por su valor neto realizable si fuera inferior."),
    ("NV6", "Norma de Valoración 6ª — Operaciones en divisas", "norma_valoracion", "Las operaciones en divisas se valorarán al tipo de cambio vigente en la fecha de la operación."),
    ("NV7", "Norma de Valoración 7ª — Deterioro y provisión", "norma_valoracion", "Se reconocerán pérdidas por deterioro cuando el valor neto de realización sea inferior al valor en libros."),
    ("NV8", "Norma de Valoración 8ª — Amortización", "norma_valoracion", "La amortización se calculará de forma sistemática a lo largo de la vida útil del activo."),
    ("NV9", "Norma de Valoración 9ª — Subvenciones oficiales", "norma_valoracion", "Las subvenciones de capital se registrarán como pasivo y se imputarán al resultado a lo largo de la vida útil del activo subyacente."),
    ("NV10", "Norma de Valoración 10ª — Instrumentos financieros derivados", "norma_valoracion", "Los instrumentos financieros derivados se valorarán a su valor razonable con cargo o abono al resultado."),
    ("NV11", "Norma de Valoración 11ª — Provisiones", "norma_valoracion", "Las provisiones para riesgos y gastos se reconocerán cuando la empresa tenga una obligación actual y sea probable una salida de recursos."),
    ("NV12", "Norma de Valoración 12ª — Ingresos", "norma_valoracion", "Los ingresos se reconocerán cuando sean realizables y pueda determinarse con fiabilidad su valor, y sean del ejercicio correspondiente."),
    ("NV13", "Norma de Valoración 13ª — Gastos", "norma_valoracion", "Los gastos se reconocerán cuando se produzcan las pérdidas subyacentes que los originan, independientemente de la fecha de su reconocimiento contable."),
    ("NV14", "Norma de Valoración 14ª — Transacciones entre partes vinculadas", "norma_valoracion", "Las transacciones entre partes vinculadas se valorarán a valores de mercado salvo que se demuestre lo contrario."),
    ("NV15", "Norma de Valoración 15ª — Activos no corrientes y grupos enajenables", "norma_valoracion", "Los activos no corrientes y grupos enajenables mantenidos para su venta se valorarán por su valor razonable menos los costes de venta."),
    ("NV16", "Norma de Valoración 16ª — Operaciones de fusión y escisión", "norma_valoracion", "Las operaciones de fusión y escisión se valorarán conforme a lo establecido en la normativa mercantil aplicable."),
    ("NV17", "Norma de Valoración 17ª — Seguros y reaseguros", "norma_valoracion", "Las primas de seguros se imputarán al ejercicio al que correspondan y las provisiones técnicas se calcularán conforme a criterios actuariales."),
    ("NV18", "Norma de Valoración 18ª — Cooperativas", "norma_valoracion", "Las cooperativas valorarán sus instrumentos financieros de patrimonio conforme a la sustancia económica de los mismos."),
    ("NV19", "Norma de Valoración 19ª — Entidades de crédito", "norma_valoracion", "Las entidades de crédito aplicarán las normas de valoración específicas establecidas para el sector bancario."),
    ("NV20", "Norma de Valoración 20ª — Activos biológicos y productos agrícolas", "norma_valoracion", "Los activos biológicos se valorarán a su valor razonable menos los costes estimados de venta cuando sea posible determinarlo fiablemente."),
]

def seed():
    import psycopg
    conn = psycopg.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    for n in NORMAS:
        codigo, titulo, tipo, texto = n
        cur.execute(
            """
            INSERT INTO pgc_norma_valoracion (id, norma_ref, articulo, descripcion, tipo_operacion, debe_haber)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(uuid.uuid5(uuid.NAMESPACE_DNS, codigo)), codigo, None, texto, tipo, None),
        )

    conn.commit()
    print(f"Seeded {len(NORMAS)} pgc_norma_valoracion records")
    conn.close()


if __name__ == "__main__":
    seed()
