import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata', cursor_factory=RealDictCursor)
cur = conn.cursor()

# Test the fallback query directly
print("=== Test fallback query ===")
cur.execute("""
    SELECT a.id AS doc_id, n.codigo, a.numero, a.tipo, va.texto,
           va.vigente_desde, va.vigente_hasta,
           ts_rank(va.search_vector, plainto_tsquery('spanish', 'IRPF modelo 100')) AS rank,
           n.boe_id, n.eli_uri
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE va.search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100')
      AND va.vigente_desde = (
          SELECT MAX(v2.vigente_desde)
          FROM version_articulo v2
          JOIN articulo a2 ON v2.articulo_id = a2.id
          WHERE a2.id = a.id
      )
    ORDER BY a.id, rank DESC, va.vigente_desde DESC
    LIMIT 10
""")
rows = cur.fetchall()
print(f"Found {len(rows)} rows")
for row in rows:
    print(f"  {row['codigo']} art. {row['numero']}: rank={row['rank']}")

# Check documento_fragmento query
print("\n=== Test chunked query ===")
cur.execute("""
    SELECT cf.documento_origen_id AS doc_id, n.codigo, a.numero,
           ts_rank(cf.search_vector, plainto_tsquery('spanish', 'IRPF modelo 100')) AS rank
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE cf.search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100')
      AND cf.documento_origen_tipo = 'legislacion'
    LIMIT 10
""")
rows = cur.fetchall()
print(f"Found {len(rows)} rows")
for row in rows:
    print(f"  {row['codigo']} art. {row['numero']}: rank={row['rank']}")

# Check what search_vector is in documento_fragmento
print("\n=== documento_fragmento search_vector ===")
cur.execute("""
    SELECT cf.id, cf.titulo, cf.search_vector::text
    FROM documento_fragmento cf
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"  cf.id={row['id']}, titulo={row['titulo']}: {row['search_vector'][:200]}")

# Check: does 'modelo' stem in spanish?
print("\n=== Stemming check ===")
cur.execute("SELECT to_tsvector('spanish', 'modelo')")
print(f"  to_tsvector('modelo'): {cur.fetchone()[0]}")
cur.execute("SELECT plainto_tsquery('spanish', 'modelo 100')")
print(f"  plainto_tsquery('modelo 100'): {cur.fetchone()[0]}")

# Check: does the search_vector in documento_fragmento contain 'modelo'?
print("\n=== Check if 'modelo' is in any df vector ===")
cur.execute("SELECT COUNT(*) FROM documento_fragmento WHERE search_vector @@ to_tsquery('spanish', 'model')")
print(f"  Matches 'model': {cur.fetchone()[0]}")

conn.close()
