from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'norma' ORDER BY ordinal_position"
    )).mappings()
    for r in rows:
        print(r)
