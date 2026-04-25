"""Debug: inspect search_vector content."""
import psycopg2

DB_URL = "postgresql://esdata:testpass@localhost:5434/esdata"

conn = psycopg2.connect(DB_URL, options="-c search_path=public")
cur = conn.cursor()

# Check search_vector content
cur.execute("""
    SELECT va.texto, va.search_vector
    FROM version_articulo va
    JOIN articulo a ON va.articulo_id = a.id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF'
    LIMIT 3
""")
rows = cur.fetchall()
for texto, sv in rows:
    print(f"Texto: {texto[:100]}...")
    print(f"search_vector: {sv}")
    print()

# Check what tsvector does with "IRPF" text
cur.execute("""
    SELECT to_tsvector('spanish', 'El contribuyente que obtenga rendimientos del trabajo estará obligado a presentar la declaración de la renta correspondiente al ejercicio mediante el modelo 100')
""")
print(f"tsvector result: {cur.fetchone()[0]}")

# Check tsquery
cur.execute("""
    SELECT to_tsquery('spanish', 'irpf:* & modelo:* & 100:*')
""")
print(f"tsquery result: {cur.fetchone()[0]}")

# Check if '100' is filtered by minlength
cur.execute("""
    SELECT to_tsvector('spanish', 'modelo 100')
""")
print(f"tsvector 'modelo 100': {cur.fetchone()[0]}")

# Check 'irpf'
cur.execute("""
    SELECT to_tsvector('spanish', 'impuesto IRPF')
""")
print(f"tsvector 'impuesto IRPF': {cur.fetchone()[0]}")

conn.close()
