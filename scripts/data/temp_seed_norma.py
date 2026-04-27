import psycopg

DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

rows = [
    ("100", "contribuyente_irpf", "anual", "campana de renta (abril-junio)", "Contribuyentes IRPF con rendimientos > 22.000€ o con rentas del capital, patrimoniales, etc.", "IRPF art. 65"),
    ("303", "empresario_profesional_iva", "trimestral", "primeros 20 dias del mes siguiente al trimestre", "Empresarios y profesionales con entregas de bienes o prestaciones de servicios", "LIVA art. 71"),
    ("124", "retenedor_irnr", "mensual", "primeros 20 dias del mes siguiente", "Entidades que retengan dividendos o rentas de capital a no residentes", "IRNR art. 25"),
    ("216", "retenedor_irnr", "mensual", "primeros 20 dias del mes siguiente", "Entidades que facturen a clientes no residentes (FactA)", "IRNR art. 14"),
    ("349", "empresario_intracomunitario", "mensual", "primeros 20 dias del mes siguiente al trimestre", "Empresarios con operaciones intracomunitarias de bienes o servicios", "LIVA operaciones intracomunitarias"),
    ("200", "sociedad_contribuyente", "anual", "primeros 6 meses del ejercicio siguiente", "Sociedades sujetas al Impuesto sobre Sociedades", "LIS art. 21"),
]

with psycopg.connect(DB) as conn:
    cur = conn.cursor()
    for codigo, cat, frec, ventana, obligados, norma_base in rows:
        cur.execute(
            """INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion,
               ventana_presentacion, canal_presentacion, obligados_resumen, norma_base, origen_metadato, estado_metadato)
               VALUES ((SELECT mc.id FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
                        WHERE m.codigo = %s AND mc.campana = '2025'),
               %s, %s, %s, 'electronica', %s, %s, 'seed_curado', 'curado')
               ON CONFLICT (campana_id) DO UPDATE SET
                   categoria_obligado = EXCLUDED.categoria_obligado,
                   obligados_resumen = EXCLUDED.obligados_resumen,
                   norma_base = EXCLUDED.norma_base,
                   actualizado_at = now()""",
            (codigo, cat, frec, ventana, obligados, norma_base),
        )
    conn.commit()
    print("Inserted norma_base for all 6 models")

    cur.execute("""
        SELECT m.codigo, mco.norma_base
        FROM aeat_modelo m
        LEFT JOIN modelo_campana mc ON mc.modelo_id = m.id AND mc.campana = '2025'
        LEFT JOIN modelo_campana_operativa mco ON mco.campana_id = mc.id
        WHERE m.codigo IN ('100','303','124','216','349','200')
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: norma_base = {row[1]}")
    conn.close()
