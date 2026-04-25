import psycopg2

conn = psycopg2.connect(
    'postgresql://esdata:testpass@localhost:5434/esdata',
    options='-c search_path=public'
)
cur = conn.cursor()
cur.execute("""
    SELECT am.codigo, am.nombre, am.impuesto, mco.norma_base
    FROM aeat_modelo am
    LEFT JOIN modelo_campana mc ON mc.modelo_id = am.id AND mc.activo = true
    LEFT JOIN modelo_campana_operativa mco ON mco.campana_id = mc.id
    WHERE LOWER(am.nombre) LIKE '%irpf%' OR LOWER(am.impuesto) LIKE '%irpf%'
""")
for row in cur.fetchall():
    print(f'codigo={row[0]:10s} nombre={row[1]:30s} impuesto={row[2]:20s} norma_base={row[3]}')

print()
cur.execute("""
    SELECT am.codigo, am.nombre, am.impuesto, mco.norma_base
    FROM aeat_modelo am
    LEFT JOIN modelo_campana mc ON mc.modelo_id = am.id AND mc.activo = true
    LEFT JOIN modelo_campana_operativa mco ON mco.campana_id = mc.id
    WHERE mco.norma_base IS NOT NULL
    ORDER BY mco.norma_base
    LIMIT 20
""")
for row in cur.fetchall():
    print(f'codigo={row[0]:10s} nombre={row[1]:30s} impuesto={row[2]:20s} norma_base={row[3]}')

conn.close()
