import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# What does to_tsquery generate for autoliquid?
cur.execute("SELECT to_tsquery('spanish', 'autoliquid')")
print(f"to_tsquery('autoliquid'): {cur.fetchone()[0]}")

# Test with exact lexema
cur.execute("SELECT to_tsvector('spanish', 'autoliquidación es el procedimiento') @@ to_tsquery('spanish', 'autoliquid')")
print(f"autoliquid match: {cur.fetchone()[0]}")

# Check all tsquery functions
cur.execute("SELECT to_tsvector('spanish', 'autoliquidación es el procedimiento') @@ to_tsquery('spanish', 'autoliquid:*)")
print(f"autoliquid:* match: {cur.fetchone()[0]}")

# What about using || & operator in plainto_tsquery?
cur.execute("SELECT plainto_tsquery('spanish', 'autoliquidacion autoliquid')")
print(f"plainto_tsquery with both: {cur.fetchone()[0]}")

# Test IRPF with modelo
cur.execute("SELECT plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"plainto_tsquery IRPF modelo 100: {cur.fetchone()[0]}")

cur.execute("SELECT to_tsvector('spanish', 'El contribuyente que obtenga rendimientos del trabajo estará obligado a presentar la declaración de la renta correspondiente al ejercicio mediante el modelo 100') @@ plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"IRPF modelo 100 plainto match: {cur.fetchone()[0]}")

# What about websearch_to_tsquery with IRPF modelo 100?
cur.execute("SELECT to_tsvector('spanish', 'El contribuyente que obtenga rendimientos del trabajo estará obligado a presentar la declaración de la renta correspondiente al ejercicio mediante el modelo 100') @@ websearch_to_tsquery('spanish', 'IRPF modelo 100')")
print(f"IRPF modelo 100 websearch match: {cur.fetchone()[0]}")

# Check search_vector for IRPF article
cur.execute("SELECT search_vector FROM version_articulo WHERE texto LIKE '%modelo 100%' LIMIT 1")
row = cur.fetchone()
if row:
    print(f"IRPF search_vector: {row[0]}")

# Check what search_vector has for LGT autoliquidacion
cur.execute("SELECT search_vector FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
row = cur.fetchone()
if row:
    print(f"LGT autoliquidacion search_vector: {row[0]}")

# The core issue: does Spanish stemmer reduce 'autoliquidacion' to 'autoliquid'?
cur.execute("SELECT ts_debug('spanish', 'autoliquidación')")
print(f"ts_debug autoliquidación: {cur.fetchone()[0]}")

cur.execute("SELECT ts_debug('spanish', 'autoliquidacion')")
print(f"ts_debug autoliquidacion: {cur.fetchone()[0]}")

cur.close()
conn.close()
