from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT a.numero, a.titulo FROM articulo a "
        "WHERE a.norma_id = (SELECT id FROM norma WHERE codigo = 'IRNR') "
        "ORDER BY a.numero"
    )).mappings()
    for r in rows:
        print(dict(r))
