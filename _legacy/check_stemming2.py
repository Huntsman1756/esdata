import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Check ts_debug for autoliquidacion
cur.execute("SELECT ts_debug('spanish', 'autoliquidación')")
print(f"ts_debug autoliquidacion: {cur.fetchone()[0]}")

cur.execute("SELECT ts_debug('spanish', 'autoliquidacion')")
print(f"ts_debug autoliquidacion (no accent): {cur.fetchone()[0]}")

# Check what to_tsquery produces
cur.execute("SELECT to_tsquery('spanish', 'autoliqu:*')")
print(f"to_tsquery autoliqu:*: {cur.fetchone()[0]}")

# Test prefix matching
cur.execute("SELECT to_tsvector('spanish', 'autoliquidación es el procedimiento') @@ to_tsquery('spanish', 'autoliqu:*')")
print(f"autoliqu:* match: {cur.fetchone()[0]}")

# Check IRPF - does to_tsvector actually produce 'irpf' token or only 'lirpf'?
cur.execute("SELECT search_vector FROM version_articulo WHERE texto LIKE '%modelo 100%' LIMIT 1")
row = cur.fetchone()
if row:
    print(f"IRPF search_vector: {row[0]}")
    has_irpf = 'irpf' in str(row[0])
    print(f"  has 'irpf' token: {has_irpf}")

# Test websearch_to_tsquery with IRPF modelo 100
cur.execute("SELECT websearch_to_tsquery('spanish', 'IRPF modelo 100')")
print(f"websearch_to_tsquery IRPF modelo 100: {cur.fetchone()[0]}")

# Test plainto_tsquery with IRPF modelo 100
cur.execute("SELECT plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"plainto_tsquery IRPF modelo 100: {cur.fetchone()[0]}")

# Check if search_vector has 'irpf' token
cur.execute("SELECT search_vector FROM version_articulo WHERE texto LIKE '%modelo 100%' LIMIT 1")
row = cur.fetchone()
if row:
    sv = str(row[0])
    print(f"\nIRPF search_vector tokens: {sv}")
    
    # Test matching with websearch
    cur.execute("SELECT search_vector @@ websearch_to_tsquery('spanish', 'IRPF modelo 100') FROM version_articulo WHERE texto LIKE '%modelo 100%' LIMIT 1")
    print(f"websearch match: {cur.fetchone()[0]}")
    
    # Test matching with plainto
    cur.execute("SELECT search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100') FROM version_articulo WHERE texto LIKE '%modelo 100%' LIMIT 1")
    print(f"plainto match: {cur.fetchone()[0]}")

# Check LGT autoliquidacion search_vector
cur.execute("SELECT search_vector FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
row = cur.fetchone()
if row:
    print(f"\nLGT autoliquidacion search_vector: {row[0]}")
    
    # Test matching
    cur.execute("SELECT search_vector @@ to_tsquery('spanish', 'autoliqu:*') FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
    print(f"autoliqu:* match: {cur.fetchone()[0]}")

cur.close()
conn.close()
