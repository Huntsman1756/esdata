import psycopg2

conn = psycopg2.connect("dbname=esdata user=esdata password=testpass host=localhost port=5434")
cur = conn.cursor()

# Verificar el texto del chunk de LIVA art 123
cur.execute("""
SELECT cf.id, cf.texto, cf.search_vector::text, cf.documento_origen_id
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
for r in cur.fetchall():
    print("Chunk ID:", r[0])
    print("Texto:", r[1])
    print("Search vector:", r[2])
    print()

# Verificar el texto del articulo version de LIVA art 123
cur.execute("""
SELECT va.texto, va.search_vector::text
FROM version_articulo va
JOIN articulo a ON a.id = va.articulo_id
JOIN norma n ON n.id = a.norma_id
WHERE n.codigo = 'LIVA' AND a.numero = '123'
""")
for r in cur.fetchall():
    print("Articulo texto:", r[0][:500])
    print("Articulo search vector:", r[1])
    print()

cur.close()
conn.close()
