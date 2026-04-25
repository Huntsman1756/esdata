import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Test: add accents to query before tsquery
cur.execute("SELECT to_tsquery('spanish', 'autoliquidación')")
print(f"to_tsquery autoliquidación: {cur.fetchone()[0]}")

cur.execute("SELECT to_tsvector('spanish', 'autoliquidación es el procedimiento') @@ to_tsquery('spanish', 'autoliquidación')")
print(f"autoliquidación match: {cur.fetchone()[0]}")

# Test with search_vector
cur.execute("SELECT search_vector @@ to_tsquery('spanish', 'autoliquidación') FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
print(f"search_vector autoliquidación match: {cur.fetchone()[0]}")

# Test IRPF with accents
cur.execute("SELECT search_vector @@ to_tsquery('spanish', 'IRPF modelo 100') FROM version_articulo WHERE texto LIKE '%modelo 100%' LIMIT 1")
print(f"IRPF modelo 100 match: {cur.fetchone()[0]}")

# Test websearch with accents
cur.execute("SELECT websearch_to_tsquery('spanish', 'autoliquidación')")
print(f"websearch autoliquidación: {cur.fetchone()[0]}")

cur.execute("SELECT search_vector @@ websearch_to_tsquery('spanish', 'autoliquidación') FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
print(f"websearch autoliquidación match: {cur.fetchone()[0]}")

cur.close()
conn.close()
