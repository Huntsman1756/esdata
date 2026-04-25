import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata', options='-c search_path=public')
cur = conn.cursor()

# Update search_vector to include codigo + titulo + texto
cur.execute("""
    UPDATE version_articulo va
    SET search_vector = to_tsvector('spanish', 
        COALESCE((SELECT n.codigo || ' ' || n.titulo || ' ' || va.texto 
                  FROM articulo a JOIN norma n ON n.id = a.norma_id 
                  WHERE a.id = va.articulo_id), va.texto)
    )
""")
print(f'Updated {cur.rowcount} rows')
conn.commit()

# Test IRPF
cur.execute("""
    SELECT n.codigo, a.numero, va.search_vector
    FROM version_articulo va
    JOIN articulo a ON va.articulo_id = a.id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF'
    LIMIT 1
""")
row = cur.fetchone()
print(f'LIRPF search_vector: {row[2]}')

cur.execute("""
    SELECT n.codigo, a.numero
    FROM version_articulo va
    JOIN articulo a ON va.articulo_id = a.id
    JOIN norma n ON n.id = a.norma_id
    WHERE va.search_vector @@ to_tsquery('spanish', 'irpf:* & model:* & 100:*')
    LIMIT 5
""")
rows = cur.fetchall()
print(f'IRPF modelo 100 results: {len(rows)}')
for r in rows:
    print(f'  {r[0]} {r[1]}')

# Test IVA
cur.execute("""
    SELECT n.codigo, a.numero
    FROM version_articulo va
    JOIN articulo a ON va.articulo_id = a.id
    JOIN norma n ON n.id = a.norma_id
    WHERE va.search_vector @@ to_tsquery('spanish', 'iva:* & libro:*')
    LIMIT 5
""")
rows = cur.fetchall()
print(f'IVA libros results: {len(rows)}')
for r in rows:
    print(f'  {r[0]} {r[1]}')

# Test LGT
cur.execute("""
    SELECT n.codigo, a.numero
    FROM version_articulo va
    JOIN articulo a ON va.articulo_id = a.id
    JOIN norma n ON n.id = a.norma_id
    WHERE va.search_vector @@ to_tsquery('spanish', 'autoliquidacion:*')
    LIMIT 5
""")
rows = cur.fetchall()
print(f'Autoliquidacion results: {len(rows)}')
for r in rows:
    print(f'  {r[0]} {r[1]}')

conn.close()
