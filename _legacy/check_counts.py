from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT n.codigo, COUNT(va.id) as articulos FROM version_articulo va "
        "JOIN articulo a ON a.id = va.articulo_id "
        "JOIN norma n ON n.id = a.norma_id "
        "GROUP BY n.codigo ORDER BY n.codigo"
    )).mappings()
    for r in rows:
        print(dict(r))
