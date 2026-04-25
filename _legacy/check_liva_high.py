from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT a.numero, LENGTH(va.texto) as len_texto "
        "FROM version_articulo va "
        "JOIN articulo a ON a.id = va.articulo_id "
        "WHERE a.norma_id = (SELECT id FROM norma WHERE codigo = 'LIVA') "
        "AND a.numero::text ~ '^[0-9]+$' "
        "AND CAST(a.numero AS integer) > 170 "
        "ORDER BY CAST(a.numero AS integer)"
    )).mappings()
    for r in rows:
        print(dict(r))
