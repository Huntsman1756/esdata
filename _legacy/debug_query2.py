import psycopg2

conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Check version_articulo rows for LIRPF art 100
print("=== version_articulo for LIRPF art 100 ===")
cur.execute("""
    SELECT va.id, va.articulo_id, va.vigente_desde, va.vigente_hasta,
           va.search_vector::text
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
    ORDER BY va.vigente_desde DESC
""")
for row in cur.fetchall():
    print(f"  va.id={row[0]}, articulo_id={row[1]}, vigente_desde={row[2]}, vector={row[4][:150]}")

# Check vig_subquery result
print("\n=== vig_subquery ===")
cur.execute("""
    SELECT a.id, MAX(v2.vigente_desde)
    FROM version_articulo v2
    JOIN articulo a2 ON v2.articulo_id = a2.id
    WHERE a2.id IN (
        SELECT a.id FROM articulo a JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo = 'LIRPF' AND a.numero = '100'
    )
    GROUP BY a.id
""")
for row in cur.fetchall():
    print(f"  articulo_id={row[0]}, max_vigente_desde={row[1]}")

# Check: what version_articulo matches the vig_subquery?
print("\n=== Matching version_articulo ===")
cur.execute("""
    SELECT va.id, va.vigente_desde, va.search_vector::text
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND a.numero = '100'
      AND va.vigente_desde = (
          SELECT MAX(v2.vigente_desde)
          FROM version_articulo v2
          JOIN articulo a2 ON v2.articulo_id = a2.id
          WHERE a2.id = a.id
      )
""")
for row in cur.fetchall():
    print(f"  va.id={row[0]}, vigente_desde={row[1]}, vector={row[2][:200]}")

# Direct match test
print("\n=== Direct match test ===")
cur.execute("""
    SELECT va.id, va.search_vector::text
    FROM version_articulo va
    WHERE va.search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100')
""")
rows = cur.fetchall()
print(f"  Matches: {len(rows)}")
for row in rows:
    print(f"    va.id={row[0]}, vector={row[1][:150]}")

# Check documento_fragmento direct match
print("\n=== documento_fragmento direct match ===")
cur.execute("""
    SELECT cf.id, cf.search_vector::text
    FROM documento_fragmento cf
    WHERE cf.search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100')
""")
rows = cur.fetchall()
print(f"  Matches: {len(rows)}")
for row in rows:
    print(f"    cf.id={row[0]}, vector={row[1][:150]}")

# Check if the issue is the DISTINCT ON + vig join mismatch
print("\n=== Full query debug ===")
cur.execute("""
    SELECT DISTINCT ON (cf.documento_origen_id)
        cf.documento_origen_id AS doc_id,
        n.codigo, a.numero,
        ts_rank(cf.search_vector, plainto_tsquery('spanish', 'IRPF modelo 100')) AS rank,
        cf.search_vector::text
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    JOIN version_articulo va ON va.articulo_id = a.id
    WHERE cf.search_vector @@ plainto_tsquery('spanish', 'IRPF modelo 100')
      AND cf.documento_origen_tipo = 'legislacion'
      AND va.vigente_desde = (
          SELECT MAX(v2.vigente_desde)
          FROM version_articulo v2
          JOIN articulo a2 ON v2.articulo_id = a2.id
          WHERE a2.id = a.id
      )
    ORDER BY cf.documento_origen_id, rank DESC, va.vigente_desde DESC
""")
rows = cur.fetchall()
print(f"  Matches: {len(rows)}")
for row in rows:
    print(f"    doc_id={row[0]}, {row[1]} art.{row[2]}, rank={row[3]}")

conn.close()
