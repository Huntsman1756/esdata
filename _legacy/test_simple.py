import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test 1: Simple OR
cur.execute("SELECT to_tsquery('spanish', 'iva') | to_tsquery('spanish', 'liv')")
print("Simple OR:", cur.fetchone()[0])

# Test 2: websearch result
cur.execute("SELECT websearch_to_tsquery('spanish', 'iva modelo')")
print("websearch:", cur.fetchone()[0])

# Test 3: OR with websearch
cur.execute("SELECT websearch_to_tsquery('spanish', 'iva modelo') | to_tsquery('spanish', 'liv')")
print("websearch | to_tsquery:", cur.fetchone()[0])

# Test 4: Full query match
cur.execute("""
SELECT cf.search_vector @@ (websearch_to_tsquery('spanish', 'Autoliquidación trimestral iva modelo 303') | to_tsquery('spanish', 'liv'))
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

# Test 5: IRPF
cur.execute("""
SELECT cf.search_vector @@ websearch_to_tsquery('spanish', 'Declaración anual irpf modelo 100')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print("IRPF art 124 match:", cur.fetchone()[0])

# Test 6: IRNR
cur.execute("""
SELECT cf.search_vector @@ (websearch_to_tsquery('spanish', 'No residente rentas inmobiliarias modelo 216') | to_tsquery('spanish', 'noresident'))
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 match:", cur.fetchone()[0])

conn.close()
