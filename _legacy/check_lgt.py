import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Check LGT articles for autoliquidacion
cur.execute("SELECT a.numero, v.search_vector FROM articulo a JOIN version_articulo v ON v.articulo_id = a.id WHERE a.norma_id IN (SELECT id FROM norma WHERE codigo = 'LGT')")
for row in cur.fetchall():
    print(f'Art {row[0]}: {row[1]}')

# Test tsquery for autoliquidacion
cur.execute("SELECT to_tsquery('spanish', 'autoliquidacion')")
print(f"tsquery autoliquidacion: {cur.fetchone()[0]}")

cur.close()
conn.close()
