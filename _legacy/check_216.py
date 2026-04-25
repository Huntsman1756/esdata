from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT mi.contenido FROM modelo_instruccion mi "
        "JOIN modelo_campana mc ON mc.id = mi.campana_id "
        "JOIN aeat_modelo am ON am.id = mc.modelo_id "
        "WHERE am.codigo = '216' AND mi.seccion = 'quien-debe'"
    )).mappings()
    for r in rows:
        print(r['contenido'][:600])
