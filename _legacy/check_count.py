from db import db_session
from sqlalchemy import text

with db_session() as db:
    rows = db.execute(text(
        "SELECT COUNT(*) as ct FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo IN ('LIVA', 'IRNR', 'LIS', 'LGT'))"
    )).mappings()
    for r in rows:
        print(dict(r))
