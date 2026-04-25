from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT va.articulo_id, LEFT(va.texto, 200) as texto_preview, LENGTH(va.texto) as len_texto "
        "FROM version_articulo va "
        "JOIN articulo a ON a.id = va.articulo_id "
        "WHERE a.norma_id = (SELECT id FROM norma WHERE codigo = 'LIVA') "
        "AND a.numero::text IN ('75', '76', '77', '78', '79') "
        "ORDER BY a.numero"
    )).mappings()
    for r in rows:
        print(dict(r))
