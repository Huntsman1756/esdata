import psycopg
DB = 'postgresql://esdata:esdata_dev@postgres:5432/esdata'
with psycopg.connect(DB) as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT n.codigo, a.numero, LEFT(v.texto, 100)
        FROM version_articulo v
        JOIN articulo a ON a.id = v.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE n.jurisdiccion = 'internacional'
          AND (LOWER(v.texto) LIKE '%fatca%' OR LOWER(n.titulo) LIKE '%fatca%')
        LIMIT 10
    """)
    for r in cur.fetchall():
        print(r)
