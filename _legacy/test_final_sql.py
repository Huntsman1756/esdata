import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test 1: websearch_to_tsquery with accented text
cur.execute("SELECT websearch_to_tsquery('spanish', 'Autoliquidación trimestral iva modelo 303')")
print("websearch accented:", cur.fetchone()[0])

# Test 2: Check if websearch_to_tsquery stems 'modelo' to 'model'
cur.execute("SELECT websearch_to_tsquery('spanish', 'modelo')")
print("websearch modelo:", cur.fetchone()[0])

# Test 3: Check if websearch_to_tsquery handles (iva | liv)
cur.execute("SELECT websearch_to_tsquery('spanish', 'autoliquidacion trimestral (iva | liv) modelo 303')")
print("websearch with OR:", cur.fetchone()[0])

# Test 4: Test the full query from _build_tsquery
# _build_tsquery returns: "Autoliquidación trimestral iva modelo 303" with extra_or=["'liv'"]
# So full_tsq = "websearch_to_tsquery('spanish', :tsquery) | ('liv')"
cur.execute("""
SELECT cf.search_vector @@ (websearch_to_tsquery('spanish', 'Autoliquidación trimestral iva modelo 303') | ('liv')) as match_test
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match (websearch | liv):", cur.fetchone()[0])

# Test 5: Check what's in the vector
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 vector:", cur.fetchone()[0])

# Test 6: IRPF query
cur.execute("""
SELECT cf.search_vector @@ websearch_to_tsquery('spanish', 'Declaración anual irpf modelo 100') as match_irpf
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print("IRPF art 124 match:", cur.fetchone()[0])

# Test 7: IRNR query
cur.execute("""
SELECT cf.search_vector @@ (websearch_to_tsquery('spanish', 'No residente rentas inmobiliarias modelo 216') | ('noresident')) as match_irnr
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 match:", cur.fetchone()[0])

conn.close()
