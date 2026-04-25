import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata', options='-c search_path=public')
cur = conn.cursor()

# Check: does IRPF appear in search_vector?
cur.execute("""
    SELECT n.codigo, va.search_vector
    FROM version_articulo va
    JOIN articulo a ON va.articulo_id = a.id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF'
    LIMIT 1
""")
row = cur.fetchone()
print(f'search_vector: {row[1]}')

# Check if 'irpf' token exists
cur.execute("""
    SELECT n.codigo,
        CASE WHEN va.search_vector @@ to_tsquery('spanish', 'irpf') THEN 'YES' ELSE 'NO' END as has_irpf,
        CASE WHEN va.search_vector @@ to_tsquery('spanish', 'lirpf') THEN 'YES' ELSE 'NO' END as has_lirpf
    FROM version_articulo va
    JOIN articulo a ON va.articulo_id = a.id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF'
    LIMIT 1
""")
row = cur.fetchone()
print(f'has_irpf: {row[1]}, has_lirpf: {row[2]}')

# The issue: LIRPF != IRPF. Need to add IRPF explicitly
# Update search_vector to include codigo + codigo_without_prefix + titulo + texto
cur.execute("""
    UPDATE version_articulo va
    SET search_vector = to_tsvector('spanish', 
        COALESCE((
            SELECT n.codigo || ' ' || 
                   CASE WHEN n.codigo LIKE 'L%' THEN SUBSTRING(n.codigo FROM 2) ELSE n.codigo END || ' ' ||
                   n.titulo || ' ' || va.texto 
            FROM articulo a JOIN norma n ON n.id = a.norma_id 
            WHERE a.id = va.articulo_id
        ), va.texto)
    )
    WHERE va.search_vector IS NOT NULL
""")
print(f'Updated {cur.rowcount} rows')
conn.commit()

# Verify
cur.execute("""
    SELECT n.codigo, va.search_vector
    FROM version_articulo va
    JOIN articulo a ON va.articulo_id = a.id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF'
    LIMIT 1
""")
row = cur.fetchone()
print(f'\nLIRPF search_vector: {row[1]}')

# Test IRPF
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

# Test LGT autoliquidacion
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
