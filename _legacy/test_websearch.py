import psycopg2

conn = psycopg2.connect("dbname=esdata user=esdata password=testpass host=localhost port=5434")
cur = conn.cursor()

# Test websearch_to_tsquery with (iva|liv) syntax
cur.execute("""
SELECT websearch_to_tsquery('spanish', 'Autoliquidacion trimestral (iva|liv) modelo 303') as tsq
""")
print("websearch_to_tsquery:", cur.fetchone()[0])

# Test match
cur.execute("""
SELECT cf.search_vector @@ websearch_to_tsquery('spanish', 'Autoliquidacion trimestral (iva|liv) modelo 303') as match_test
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
print("Match LIVA art 123:", cur.fetchone()[0])

# Test with plain query (no (iva|liv))
cur.execute("""
SELECT cf.search_vector @@ websearch_to_tsquery('spanish', 'Autoliquidacion trimestral iva modelo 303') as match_plain
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
print("Match plain iva:", cur.fetchone()[0])

# Test with 'lirnr|noresident'
cur.execute("""
SELECT websearch_to_tsquery('spanish', 'IRNR no residente modelo 216') as tsq_irnr
""")
print("tsquery IRNR:", cur.fetchone()[0])

cur.close()
conn.close()
