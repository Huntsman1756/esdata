import sys
sys.path.insert(0, '/app')
from db import engine
from sqlalchemy import text

with engine.connect() as conn:
    # IRNR chunks total
    count = conn.execute(text("SELECT COUNT(*) FROM documento_fragmento cf JOIN articulo a ON a.id = cf.documento_origen_id JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'IRNR'"))
    print("IRNR chunks total:", count.scalar())

    # Tipo distribution
    tipos = conn.execute(text("SELECT cf.documento_origen_tipo, COUNT(*) FROM documento_fragmento cf JOIN articulo a ON a.id = cf.documento_origen_id JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'IRNR' GROUP BY cf.documento_origen_tipo"))
    print("Tipo distribution:", tipos.fetchall())

    # IRNR articulos versions
    vig = conn.execute(text("SELECT a.id, a.numero, va.vigente_desde FROM articulo a JOIN norma n ON n.id = a.norma_id JOIN version_articulo va ON va.articulo_id = a.id WHERE n.codigo = 'IRNR' ORDER BY a.id, va.vigente_desde DESC LIMIT 5"))
    print("IRNR articulos versions:")
    for r in vig.fetchall():
        print("  ", r)

    # Run the EXACT query from _search_legislacion_pg
    q = """SELECT * FROM (
        SELECT DISTINCT ON (cf.documento_origen_id)
            cf.documento_origen_id AS doc_id, n.codigo, a.numero, va.vigente_desde,
            0.0 AS rank, cf.texto AS chunk_texto, cf.id AS chunk_id
        FROM documento_fragmento cf
        JOIN articulo a ON a.id = cf.documento_origen_id
        JOIN norma n ON n.id = a.norma_id
        JOIN version_articulo va ON va.articulo_id = a.id
        WHERE n.codigo = 'IRNR'
            AND TRUE
            AND cf.documento_origen_tipo = 'legislacion'
            AND va.vigente_desde = (
                SELECT MAX(v2.vigente_desde)
                FROM version_articulo v2
                JOIN articulo a2 ON v2.articulo_id = a2.id
                WHERE a2.id = a.id
            )
        ORDER BY cf.documento_origen_id, rank DESC, va.vigente_desde DESC
    ) AS sub
    ORDER BY rank DESC
    LIMIT 10
    """
    rows = list(conn.execute(text(q)).mappings())
    print("Query results:", len(rows))
    for r in rows[:3]:
        print("  doc_id=", r["doc_id"], "codigo=", r["codigo"], "numero=", r["numero"])
