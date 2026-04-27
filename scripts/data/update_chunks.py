import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata', options='-c search_path=public')
cur = conn.cursor()

# Update documento_fragmento search_vector with norma prefix
cur.execute("""
    UPDATE documento_fragmento cf
    SET search_vector = to_tsvector('spanish',
        COALESCE((
            SELECT n.codigo || ' ' || 
                   CASE WHEN n.codigo LIKE 'L%' THEN SUBSTRING(n.codigo FROM 2) ELSE n.codigo END || ' ' ||
                   cf.titulo || ' ' || cf.texto
            FROM articulo a JOIN norma n ON n.id = a.norma_id
            WHERE a.id = cf.documento_origen_id
        ), cf.texto)
    )
    WHERE cf.documento_origen_tipo = 'legislacion'
""")
print(f'Updated documento_fragmento: {cur.rowcount} rows')
conn.commit()

# Verify chunks now work
cur.execute("""
    SELECT cf.texto, cf.search_vector, n.codigo
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIRPF' AND cf.chunk_index = 0
    LIMIT 1
""")
row = cur.fetchone()
print(f'\nLIRPF chunk search_vector: {row[1]}')

cur.execute("""
    SELECT cf.titulo, n.codigo, a.numero
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE cf.search_vector @@ to_tsquery('spanish', 'irpf:* & model:* & 100:*')
    LIMIT 5
""")
rows = cur.fetchall()
print(f'IRPF modelo 100 (chunks): {len(rows)}')
for r in rows:
    print(f'  {r[1]} {r[2]}: {r[0]}')

# Test autoliquidacion
cur.execute("""
    SELECT n.codigo, a.numero
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE cf.search_vector @@ to_tsquery('spanish', 'autoliquidacion:*')
    LIMIT 5
""")
rows = cur.fetchall()
print(f'\nAutoliquidacion (chunks): {len(rows)}')
for r in rows:
    print(f'  {r[0]} {r[1]}')

# Test LGT prescripcion
cur.execute("""
    SELECT n.codigo, a.numero
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE cf.search_vector @@ to_tsquery('spanish', 'lgt:* & prescripcion:* & deuda:*')
    LIMIT 5
""")
rows = cur.fetchall()
print(f'\nLGT prescripcion (chunks): {len(rows)}')
for r in rows:
    print(f'  {r[0]} {r[1]}')

conn.close()
