import psycopg2

conn = psycopg2.connect("dbname=esdata user=esdata password=testpass host=localhost port=5434")
cur = conn.cursor()

# Verificar que el problema es 'iva' vs 'liv'
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'modelo 303') as match_sin_iva
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
print("match_sin_iva:", cur.fetchone()[0])

cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'modelo 303 liv') as match_liv
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
print("match_liv:", cur.fetchone()[0])

cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'modelo 303 iva') as match_iva
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
print("match_iva:", cur.fetchone()[0])

print()

# Verificar si hay articulos LIVA con 'iva' en search_vector
cur.execute("""
SELECT n.codigo, a.numero, va.search_vector::text
FROM version_articulo va
JOIN articulo a ON a.id = va.articulo_id
JOIN norma n ON n.id = a.norma_id
WHERE n.codigo = 'LIVA'
  AND va.search_vector::text LIKE '%iva%'
LIMIT 5
""")
for row in cur.fetchall():
    print("LIVA", row[0], "art", row[1], ":", row[2][:200])

print()

# Verificar articulos LIVA con 'liv' en search_vector
cur.execute("""
SELECT n.codigo, a.numero, va.search_vector::text
FROM version_articulo va
JOIN articulo a ON a.id = va.articulo_id
JOIN norma n ON n.id = a.norma_id
WHERE n.codigo = 'LIVA'
  AND va.search_vector::text LIKE '%liv%'
LIMIT 5
""")
for row in cur.fetchall():
    print("LIVA", row[0], "art", row[1], ": tiene 'liv'")

cur.close()
conn.close()
