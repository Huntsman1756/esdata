import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test: cast string to tsquery
cur.execute("SELECT ('iva' | 'liv')::tsquery")
print("String cast:", cur.fetchone()[0])

# Test: websearch | string cast
cur.execute("SELECT websearch_to_tsquery('spanish', 'iva modelo') | ('liv'::tsquery)")
print("websearch | cast:", cur.fetchone()[0])

# Test: full match
cur.execute("""
SELECT cf.search_vector @@ (websearch_to_tsquery('spanish', 'Autoliquidación trimestral iva modelo 303') | ('liv'::tsquery))
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match:", cur.fetchone()[0])

# Check vector
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 vector:", cur.fetchone()[0])

# IRPF
cur.execute("""
SELECT cf.search_vector @@ websearch_to_tsquery('spanish', 'Declaración anual irpf modelo 100')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print("IRPF art 124 match:", cur.fetchone()[0])

# IRNR
cur.execute("""
SELECT cf.search_vector @@ (websearch_to_tsquery('spanish', 'No residente rentas inmobiliarias modelo 216') | ('noresident'::tsquery))
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 match:", cur.fetchone()[0])

conn.close()
