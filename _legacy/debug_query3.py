import psycopg2

conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Check plainto_tsquery behavior
print("=== plainto_tsquery behavior ===")
cur.execute("SELECT plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"  plainto_tsquery('IRPF modelo 100'): {cur.fetchone()[0]}")

cur.execute("SELECT plainto_tsquery('spanish', 'lirpf modelo 100')")
print(f"  plainto_tsquery('lirpf modelo 100'): {cur.fetchone()[0]}")

cur.execute("SELECT plainto_tsquery('spanish', 'modelo 100')")
print(f"  plainto_tsquery('modelo 100'): {cur.fetchone()[0]}")

cur.execute("SELECT plainto_tsquery('spanish', 'IRPF')")
print(f"  plainto_tsquery('IRPF'): {cur.fetchone()[0]}")

# Check what the vector actually contains for 'lirpf'
print("\n=== Vector contents ===")
cur.execute("""
    SELECT va.id, va.search_vector::text
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
""")
row = cur.fetchone()
print(f"  va.id={row[0]}, vector={row[1]}")

# Does 'lirpf' appear in the vector?
print(f"  Contains 'lirpf': {'lirpf' in row[1]}")
print(f"  Contains 'irpf': {'irpf' in row[1]}")
print(f"  Contains 'model': {'model' in row[1]}")
print(f"  Contains '100': {'100' in row[1]}")

# Test the exact match
print("\n=== Exact match tests ===")
cur.execute("SELECT to_tsvector('spanish', 'LIRPF 100 De Anual IRPF Modelo') @@ plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"  Sample text @@ plainto_tsquery: {cur.fetchone()[0]}")

# Check: what does the actual va.search_vector match?
cur.execute("""
    SELECT va.search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100')
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
""")
print(f"  Actual va.search_vector @@ plainto_tsquery: {cur.fetchone()[0]}")

# Check documento_fragmento
print("\n=== documento_fragmento ===")
cur.execute("""
    SELECT cf.id, cf.search_vector::text, cf.titulo
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
""")
for row in cur.fetchall():
    print(f"  cf.id={row[0]}, vector={row[1][:200]}")
    print(f"    Contains 'lirpf': {'lirpf' in row[1]}")
    print(f"    Contains 'irpf': {'irpf' in row[1]}")
    print(f"    Contains 'model': {'model' in row[1]}")
    print(f"    Contains '100': {'100' in row[1]}")

# Test df match
cur.execute("""
    SELECT cf.search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100')
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
""")
print(f"\n  df.search_vector @@ plainto_tsquery: {cur.fetchone()[0]}")

conn.close()
