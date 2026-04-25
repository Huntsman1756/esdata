import sys
sys.path.insert(0, '/app')

from db import db_session
from sqlalchemy import text

q = 'IRNR rentas sin establecimiento permanente'

with db_session() as db:
    # Test 1: direct SQL with literal values
    sql1 = "SELECT cf.documento_origen_id, n.codigo, a.numero FROM documento_fragmento cf JOIN articulo a ON a.id = cf.documento_origen_id JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'IRNR' AND cf.search_vector @@ (plainto_tsquery('spanish', 'IRNR') || plainto_tsquery('spanish', 'IRNR')) AND cf.documento_origen_tipo = 'legislacion' LIMIT 5"
    r1 = db.execute(text(sql1)).fetchall()
    print('Test 1 (literal SQL):', len(r1), 'rows')
    
    # Test 2: with bindparams
    sql2 = "SELECT cf.documento_origen_id, n.codigo, a.numero FROM documento_fragmento cf JOIN articulo a ON a.id = cf.documento_origen_id JOIN norma n ON n.id = a.norma_id WHERE n.codigo = :norma AND cf.search_vector @@ (plainto_tsquery('spanish', :tsq) || plainto_tsquery('spanish', :accents)) AND cf.documento_origen_tipo = 'legislacion'"
    query = text(sql2)
    query_with_binds = query.bindparams(norma='IRNR', tsq='IRNR', accents='IRNR')
    r2 = db.execute(query_with_binds).fetchall()
    print('Test 2 (bindparams):', len(r2), 'rows')
    
    # Test 3: with bindparams + execute params
    r3 = db.execute(query_with_binds, {'norma': 'IRNR'}).fetchall()
    print('Test 3 (bindparams + execute params):', len(r3), 'rows')
    
    # Test 4: full query like the real code
    sql4 = """
    SELECT * FROM (
        SELECT DISTINCT ON (cf.documento_origen_id)
            cf.documento_origen_id AS doc_id,
            n.codigo,
            a.numero,
            a.tipo,
            (SELECT va.texto FROM version_articulo va JOIN articulo a2 ON a2.id = va.articulo_id WHERE a2.id = cf.documento_origen_id ORDER BY va.vigente_desde DESC LIMIT 1) AS texto,
            (SELECT MAX(v2.vigente_desde) FROM version_articulo v2 JOIN articulo a2 ON v2.articulo_id = a2.id WHERE a2.id = cf.documento_origen_id) AS vigente_desde,
            (SELECT MAX(v2.vigente_hasta) FROM version_articulo v2 JOIN articulo a2 ON v2.articulo_id = a2.id WHERE a2.id = cf.documento_origen_id) AS vigente_hasta,
            ts_rank(cf.search_vector, plainto_tsquery('spanish', :tsq) || plainto_tsquery('spanish', :accents)) AS rank,
            cf.texto AS chunk_texto,
            cf.id AS chunk_id
        FROM documento_fragmento cf
        JOIN articulo a ON a.id = cf.documento_origen_id
        JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo = :norma
          AND cf.search_vector @@ (plainto_tsquery('spanish', :tsq) || plainto_tsquery('spanish', :accents))
          AND cf.documento_origen_tipo = 'legislacion'
    ) AS sub
    ORDER BY rank DESC
    LIMIT 10
    """
    query4 = text(sql4)
    query4_with_binds = query4.bindparams(norma='IRNR', tsq='IRNR', accents='IRNR')
    r4 = db.execute(query4_with_binds).fetchall()
    print('Test 4 (full query):', len(r4), 'rows')
    for row in r4[:3]:
        print('  ', dict(row))
