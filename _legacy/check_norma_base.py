import psycopg2

conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata', options='-c search_path=public')
cur = conn.cursor()

# Check what search_legislacion returns for IRPF query
cur.execute("""
    SELECT DISTINCT ON (n.codigo) n.codigo, a.numero, LEFT(va.texto, 200) as texto
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    JOIN version_articulo va ON va.articulo_id = a.id
    WHERE cf.documento_origen_tipo = 'legislacion'
      AND cf.search_vector @@ to_tsquery('spanish', 'irpf')
      AND va.vigente_desde = (
          SELECT MAX(v2.vigente_desde)
          FROM version_articulo v2
          JOIN articulo a2 ON a2.id = v2.articulo_id
          WHERE a2.id = cf.documento_origen_id
      )
    ORDER BY n.codigo, ts_rank(cf.search_vector, to_tsquery('spanish', 'irpf')) DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f'codigo={row[0]} articulo={row[1]} texto={row[2][:100]}')

print()
print("--- norma_base for model 100 ---")
cur.execute("""
    SELECT am.codigo, am.nombre, mco.norma_base
    FROM aeat_modelo am
    LEFT JOIN modelo_campana mc ON mc.modelo_id = am.id AND mc.activo = true
    LEFT JOIN modelo_campana_operativa mco ON mco.campana_id = mc.id
    WHERE am.codigo = '100'
""")
for row in cur.fetchall():
    print(f'codigo={row[0]} nombre={row[1]} norma_base={row[2]}')

conn.close()
