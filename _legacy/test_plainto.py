import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test: to_tsquery con texto acentado - stemma automáticamente?
cur.execute("SELECT to_tsquery('spanish', 'autoliquidación & trimestral & iva & modelo & 303')")
print("to_tsquery accented:", cur.fetchone()[0])

# Test: plainto_tsquery con texto
cur.execute("SELECT plainto_tsquery('spanish', 'Autoliquidación trimestral iva modelo 303')")
print("plainto_tsquery:", cur.fetchone()[0])

# Test: match con plainto_tsquery
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'Autoliquidación trimestral iva modelo 303')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match:", cur.fetchone()[0])

# Test: plainto_tsquery para IRPF
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'Declaración anual irpf modelo 100')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print("IRPF art 124 match:", cur.fetchone()[0])

# Test: plainto_tsquery para IRNR
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'No residente rentas inmobiliarias modelo 216')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 match:", cur.fetchone()[0])

# Test: plainto_tsquery con OR - (iva | liv)
cur.execute("SELECT plainto_tsquery('spanish', 'autoliquidación trimestral (iva | liv) modelo 303')")
print("plainto_tsquery with OR:", cur.fetchone()[0])

# Test: plainto_tsquery con IRNR + noresident
cur.execute("SELECT plainto_tsquery('spanish', 'no residente rentas inmobiliarias modelo 216')")
print("plainto_tsquery IRNR:", cur.fetchone()[0])

# Check IRNR vector
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 vector:", cur.fetchone()[0])

conn.close()
