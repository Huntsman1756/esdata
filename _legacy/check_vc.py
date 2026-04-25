import psycopg
DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"
with psycopg.connect(DB) as conn:
    cur = conn.cursor()
    cur.execute("SELECT constraint_name, constraint_type FROM information_schema.table_constraints WHERE table_name = 'version_articulo'")
    for r in cur.fetchall():
        print(r)
