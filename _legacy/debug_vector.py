import sys, os
sys.path.insert(0, 'apps/api')
os.environ['DATABASE_URL'] = 'postgresql+psycopg://esdata:testpass@localhost:5434/esdata'

import psycopg2

conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Check search_vector content
cur.execute("""
    SELECT n.codigo, n.titulo, a.numero, a.contenido, a.search_vector::text
    FROM articulo a
    JOIN norma n ON a.norma_id = n.id
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"Norma: {row[0]}, Art: {row[2]}")
    print(f"  Vector: {row[4][:200]}")
    print(f"  Texto: {row[3][:100]}")
    print()

# Check what tsvector matches for 'irpf'
print("=== tsvector for 'irpf' ===")
cur.execute("SELECT to_tsvector('spanish', 'LIRPF')")
print(f"  LIRPF -> {cur.fetchone()[0]}")
cur.execute("SELECT to_tsvector('spanish', 'IRPF')")
print(f"  IRPF -> {cur.fetchone()[0]}")
cur.execute("SELECT to_tsvector('spanish', 'Ley 37/1992')")
print(f"  Ley 37/1992 -> {cur.fetchone()[0]}")
cur.execute("SELECT to_tsvector('spanish', 'IVA')")
print(f"  IVA -> {cur.fetchone()[0]}")

# Check what tsquery matches
print("\n=== tsquery matching ===")
cur.execute("SELECT to_tsvector('spanish', 'LIRPF') @@ to_tsquery('spanish', 'lirpf')")
print(f"  LIRPF @@ lirpf: {cur.fetchone()[0]}")
cur.execute("SELECT to_tsvector('spanish', 'LIRPF') @@ to_tsquery('spanish', 'irpf')")
print(f"  LIRPF @@ irpf: {cur.fetchone()[0]}")

# Check plainto_tsquery
cur.execute("SELECT plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"\n  plainto_tsquery('IRPF modelo 100'): {cur.fetchone()[0]}")

# Check what search_vector actually contains for IRPF articles
print("\n=== IRPF articles search_vector ===")
cur.execute("""
    SELECT n.codigo, a.numero, a.search_vector::text
    FROM articulo a
    JOIN norma n ON a.norma_id = n.id
    WHERE n.codigo ILIKE '%lirpf%' OR n.codigo ILIKE '%irpf%'
""")
for row in cur.fetchall():
    print(f"  {row[0]} art. {row[1]}: {row[2][:300]}")

conn.close()
