from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT n.codigo, n.titulo, n.tipo, n.año FROM norma n ORDER BY n.codigo"
    )).mappings()
    for r in rows:
        print(dict(r))
