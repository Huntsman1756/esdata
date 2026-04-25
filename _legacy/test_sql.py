import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test plainto_tsquery directly
cur.execute("SELECT plainto_tsquery('spanish', 'Autoliquidación')")
print("1:", cur.fetchone()[0])

cur.execute("SELECT plainto_tsquery('spanish', 'iva')")
print("2:", cur.fetchone()[0])

# Test full tsquery construction
cur.execute("""
SELECT to_tsvector('spanish', 'LIRPF autoliquidacion modelo 100')
""")
vec = cur.fetchone()[0]
print("vector:", vec)

# Test the tsquery that _build_tsquery generates
tsq = "plainto_tsquery('spanish', 'Autoliquidación') & plainto_tsquery('spanish', 'modelo') & plainto_tsquery('spanish', '100')"
print("tsq:", tsq)

cur.execute(f"SELECT to_tsvector('spanish', 'LIRPF autoliquidacion modelo 100') @@ ({tsq})")
print("match:", cur.fetchone()[0])

# Test with OR for iva
tsq2 = "plainto_tsquery('spanish', 'Autoliquidación') & plainto_tsquery('spanish', 'trimestral') & (plainto_tsquery('spanish', 'iva') | plainto_tsquery('spanish', 'liv')) & plainto_tsquery('spanish', 'modelo') & plainto_tsquery('spanish', '303')"
print("tsq2:", tsq2)

cur.execute(f"""
SELECT cf.search_vector @@ ({tsq2}) as match_test
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match:", cur.fetchone()[0])

# Check what's in the vector for LIVA art 123
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
vec2 = cur.fetchone()[0]
print("LIVA art 123 vector:", vec2)

conn.close()
