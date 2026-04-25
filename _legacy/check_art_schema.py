from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'articulo' ORDER BY ordinal_position"
    )).mappings()
    for r in rows:
        print(dict(r))
