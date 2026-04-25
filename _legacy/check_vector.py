import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Check search_vector for LIRPF articles
cur.execute("""
    SELECT n.codigo, a.numero, va.search_vector::text
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF'
""")
for row in cur.fetchall():
    print(f"LIRPF art. {row[1]}: {row[2][:300]}")

# Check what tsquery matches
print("\n=== tsquery test ===")
cur.execute("SELECT to_tsvector('spanish', 'LIRPF 100 De Anual IRPF Modelo')")
v = cur.fetchone()[0]
print(f"Sample vector: {v}")
cur.execute("SELECT to_tsquery('spanish', 'irpf')")
q = cur.fetchone()[0]
print(f"tsquery 'irpf': {q}")
cur.execute("SELECT to_tsvector('spanish', 'LIRPF 100 De Anual IRPF Modelo') @@ to_tsquery('spanish', 'irpf')")
print(f"matches: {cur.fetchone()[0]}")

# Check plainto_tsquery
cur.execute("SELECT plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"plainto_tsquery: {cur.fetchone()[0]}")

# Check if search_vector contains 'modelo'
cur.execute("SELECT to_tsvector('spanish', 'modelo')")
print(f"to_tsvector('modelo'): {cur.fetchone()[0]}")
cur.execute("SELECT to_tsvector('spanish', '100')")
print(f"to_tsvector('100'): {cur.fetchone()[0]}")

conn.close()
