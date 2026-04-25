import psycopg2

conn = psycopg2.connect("dbname=esdata user=esdata password=testpass host=localhost port=5434")
cur = conn.cursor()

# Check LIVA search_vector - does it contain 'iva' or just 'liv'?
cur.execute("""
SELECT n.codigo, a.numero, va.search_vector,
       cf.search_vector
FROM version_articulo va
JOIN articulo a ON a.id = va.articulo_id
JOIN norma n ON n.id = a.norma_id
LEFT JOIN documento_fragmento cf ON cf.documento_origen_id = a.id
WHERE n.codigo = 'LIVA' AND a.numero = '123'
LIMIT 1
""")
row = cur.fetchone()
print("LIVA art 123 search_vector:", row[2])
print("LIVA art 123 chunk search_vector:", row[3])

print()

# Test: does the search_vector match the tsquery?
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'Autoliquidacion trimestral IVA modelo 303') as match_plain,
       cf.search_vector @@ plainto_tsquery('spanish', 'autoliquidación trimestral IVA modelo 303') as match_acc,
       cf.search_vector @@ plainto_tsquery('spanish', 'autoliquidacion IVA modelo 303') as match_noautoli,
       cf.search_vector @@ plainto_tsquery('spanish', 'LIVA modelo 303') as match_liva,
       cf.search_vector @@ plainto_tsquery('spanish', 'modelo 303') as match_modelo303
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
r = cur.fetchone()
print("match_plain (autoliquidacion):", r[0])
print("match_acc (autoliquidación):", r[1])
print("match_noautoli (sin autoliquidacion):", r[2])
print("match_liva:", r[3])
print("match_modelo303:", r[4])

print()

# Check if 'iva' appears in any LIVA search_vector
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

# Check what plainto_tsquery does with 'LIVA'
cur.execute("SELECT plainto_tsquery('spanish', 'LIVA')")
print("plainto_tsquery('LIVA'):", cur.fetchone()[0])

cur.execute("SELECT plainto_tsquery('spanish', 'IVA')")
print("plainto_tsquery('IVA'):", cur.fetchone()[0])

cur.execute("SELECT plainto_tsquery('spanish', 'liva')")
print("plainto_tsquery('liva'):", cur.fetchone()[0])

cur.execute("SELECT plainto_tsquery('spanish', 'iva')")
print("plainto_tsquery('iva'):", cur.fetchone()[0])

cur.close()
conn.close()
