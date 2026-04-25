import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Test with normalized query (autoliquidación)
cur.execute("SELECT search_vector @@ to_tsquery('spanish', 'autoliquidación') FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
print(f"search_vector autoliquidación match: {cur.fetchone()[0]}")

cur.execute("SELECT search_vector @@ websearch_to_tsquery('spanish', 'autoliquidación') FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
print(f"websearch autoliquidación match: {cur.fetchone()[0]}")

# Test IRPF modelo 100
cur.execute("SELECT search_vector @@ to_tsquery('spanish', 'IRPF modelo 100') FROM version_articulo WHERE texto LIKE '%modelo 100%' LIMIT 1")
print(f"IRPF modelo 100 match: {cur.fetchone()[0]}")

# Test IVA libros
cur.execute("SELECT search_vector @@ to_tsquery('spanish', 'IVA libros') FROM version_articulo WHERE texto LIKE '%tipo reducido%' LIMIT 1")
print(f"IVA libros match: {cur.fetchone()[0]}")

cur.close()
conn.close()
