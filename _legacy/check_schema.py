import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@postgres:5432/esdata")
eng = create_engine(DB_URL)

with eng.connect() as c:
    for tbl in ["version_articulo", "documento_fragmento", "documento_interpretativo"]:
        print(f"\n=== {tbl} ===")
        try:
            rs = c.execute(text(
                "SELECT column_name, data_type, udt_name "
                "FROM information_schema.columns "
                "WHERE table_name = :t ORDER BY ordinal_position"
            ), {"t": tbl})
            for r in rs:
                print(f"  {r[0]}: {r[1]} ({r[2]})")
        except Exception as e:
            print(f"  ERROR: {e}")
