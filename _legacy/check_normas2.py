from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT codigo, titulo, tipo_fuente, vigente_desde, estado_cobertura FROM norma ORDER BY codigo"
    )).mappings()
    for r in rows:
        print(dict(r))
