import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata', options='-c search_path=public')
cur = conn.cursor()

# Check LGT 130 chunk content
cur.execute("""
    SELECT cf.texto, cf.search_vector, cf.chunk_index
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LGT' AND a.numero = '130'
    ORDER BY cf.chunk_index
""")
rows = cur.fetchall()
print(f'LGT 130 chunks: {len(rows)}')
for r in rows:
    print(f'  chunk {r[2]}: {r[0][:100]}')
    print(f'    sv: {r[1]}')

# Check if autoliquidacion is in the text
cur.execute("""
    SELECT cf.texto
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LGT' AND a.numero = '130'
""")
rows = cur.fetchall()
for r in rows:
    print(f'\nTexto completo: {r[0]}')
    print(f'Contains autoliquidacion: {"autoliquidacion" in r[0].lower()}')
    print(f'Contains autoliquidación: {"autoliquidación" in r[0]}')

# Test ILIKE fallback
cur.execute("""
    SELECT cf.texto
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LGT' AND a.numero = '130'
    AND cf.texto ILIKE '%autoliquidacion%'
""")
rows = cur.fetchall()
print(f'\nILIKE autoliquidacion: {len(rows)}')

conn.close()
