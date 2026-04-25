import psycopg
DB = 'postgresql://esdata:esdata_dev@postgres:5432/esdata'
with psycopg.connect(DB) as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT codigo, titulo, jurisdiccion, tipo_documento
        FROM norma
        WHERE jurisdiccion IN ('internacional','ue')
        LIMIT 10
    """)
    for r in cur.fetchall():
        print(r)
    print('---')
    cur.execute("""
        SELECT n.codigo, a.numero, LEFT(v.texto, 100)
        FROM version_articulo v
        JOIN articulo a ON a.id = v.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE n.jurisdiccion = 'internacional'
          AND LOWER(v.texto) LIKE '%fatca%'
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(r)
    print('---')
    cur.execute("""
        SELECT n.codigo, a.numero, LEFT(v.texto, 100)
        FROM version_articulo v
        JOIN articulo a ON a.id = v.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE n.jurisdiccion = 'internacional'
          AND LOWER(v.texto) LIKE '%w-8ben%'
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(r)
    print('---')
    cur.execute("""
        SELECT n.codigo, a.numero, LEFT(v.texto, 100)
        FROM version_articulo v
        JOIN articulo a ON a.id = v.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE n.jurisdiccion = 'internacional'
          AND LOWER(v.texto) LIKE '%crs%'
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(r)
    print('---')
    cur.execute("""
        SELECT n.codigo, a.numero, LEFT(v.texto, 100)
        FROM version_articulo v
        JOIN articulo a ON a.id = v.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE n.jurisdiccion = 'internacional'
          AND (LOWER(v.texto) LIKE '%tax%' OR LOWER(v.texto) LIKE '%information%')
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(r)
