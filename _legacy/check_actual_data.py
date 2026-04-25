import psycopg2

conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Check what texto is actually stored
cur.execute("""
    SELECT va.texto FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
""")
texto = cur.fetchone()[0]
print(f"texto starts with: {texto[:80]}")
print(f"texto ends with: {texto[-80:]}")

# Check search_vector
cur.execute("""
    SELECT va.search_vector::text FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
""")
vec = cur.fetchone()[0]
print(f"\nsearch_vector: {vec[:300]}")

# Check if 'lirpf' is in vector
print(f"\nContains 'lirpf': {'lirpf' in vec}")
print(f"Contains 'irpf': {'irpf' in vec}")

# Check what the first 5 tokens are
tokens = vec.split()
print(f"First 5 tokens: {tokens[:5]}")

# Test: does to_tsvector produce lirpf?
cur.execute("SELECT to_tsvector('spanish', 'LIRPF')")
print(f"\nto_tsvector('spanish', 'LIRPF'): {cur.fetchone()[0]}")

cur.execute("SELECT to_tsvector('spanish', 'LIRPF IRPF')")
print(f"to_tsvector('spanish', 'LIRPF IRPF'): {cur.fetchone()[0]}")

# Test plainto_tsquery
cur.execute("SELECT plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"plainto_tsquery('IRPF modelo 100'): {cur.fetchone()[0]}")

# Test: does the vector match?
cur.execute("""
    SELECT va.search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100')
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
""")
print(f"Vector @@ plainto_tsquery('IRPF modelo 100'): {cur.fetchone()[0]}")

# Check: what about just 'model' & '100'?
cur.execute("SELECT plainto_tsquery('spanish', 'modelo 100')")
print(f"plainto_tsquery('modelo 100'): {cur.fetchone()[0]}")

cur.execute("""
    SELECT va.search_vector @@ to_tsquery('spanish', 'model & 100')
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
""")
print(f"Vector @@ 'model & 100': {cur.fetchone()[0]}")

conn.close()
