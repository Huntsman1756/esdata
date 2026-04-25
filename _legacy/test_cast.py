import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test with ::tsquery cast
cur.execute("""
SELECT cf.search_vector @@ (websearch_to_tsquery('spanish', 'Autoliquidación trimestral iva modelo 303') | ('liv'::tsquery)) as match_test
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match:", cur.fetchone()[0])

# Check vector content
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 vector:", cur.fetchone()[0])

# Test IRPF
cur.execute("""
SELECT cf.search_vector @@ websearch_to_tsquery('spanish', 'Declaración anual irpf modelo 100') as match_irpf
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print("IRPF art 124 match:", cur.fetchone()[0])

# Test IRNR with fallback
cur.execute("""
SELECT cf.search_vector @@ (websearch_to_tsquery('spanish', 'No residente rentas inmobiliarias modelo 216') | ('noresident'::tsquery)) as match_irnr
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 match:", cur.fetchone()[0])

conn.close()
