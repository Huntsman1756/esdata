import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Test prefix matching with websearch
cur.execute("SELECT websearch_to_tsquery('spanish', 'autoliquidacion:*')")
print(f"websearch autoliquidacion:*: {cur.fetchone()[0]}")

# Test matching
cur.execute("SELECT to_tsvector('spanish', 'autoliquidación es el procedimiento') @@ to_tsquery('spanish', 'autoliquidacion:*')")
print(f"autoliquidacion:* match with tsvector: {cur.fetchone()[0]}")

# Test with search_vector
cur.execute("SELECT search_vector @@ to_tsquery('spanish', 'autoliquidacion:*') FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
print(f"search_vector autoliquidacion:* match: {cur.fetchone()[0]}")

# Test IRPF with prefix
cur.execute("SELECT search_vector @@ to_tsquery('spanish', 'IRPF:* modelo:* 100:*') FROM version_articulo WHERE texto LIKE '%modelo 100%' LIMIT 1")
print(f"IRPF:* modelo:* 100:* match: {cur.fetchone()[0]}")

# What about websearch with prefix?
cur.execute("SELECT to_tsvector('spanish', 'autoliquidación es el procedimiento') @@ websearch_to_tsquery('spanish', 'autoliquidacion:*')")
print(f"websearch autoliquidacion:* match: {cur.fetchone()[0]}")

# Check what websearch_to_tsquery produces with multiple terms and prefix
cur.execute("SELECT websearch_to_tsquery('spanish', 'IRPF:* modelo:* 100:*')")
print(f"websearch IRPF:* modelo:* 100:*: {cur.fetchone()[0]}")

cur.close()
conn.close()
