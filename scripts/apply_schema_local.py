"""Apply all SQL schema files to the local pgvector container."""
import psycopg2
from pathlib import Path

DB_URL = "postgresql://esdata:testpass@localhost:5434/esdata"

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

# Check pgvector extension
cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
if not cur.fetchone():
    print("Creating pgvector extension...")
    cur.execute("CREATE EXTENSION vector")
    print("Done")

# Apply SQL files in order
for sql_file in [
    "infra/sql/init.sql",
    "infra/sql/002_fulltext_search.sql",
    "infra/sql/004_norma_classification.sql",
]:
    sql = Path(sql_file).read_text(encoding='utf-8')
    cur.execute(sql)
    print(f"{sql_file} applied")

# Apply chunking schema from Alembic migration (creates documento_fragmento)
print("Applying chunking schema from Alembic...")
migration = Path("alembic/versions/20260424_0005_chunking_schema.py").read_text(encoding='utf-8')
# Extract the upgrade() function SQL statements
import re
upgrade_func = re.search(r'def upgrade\(\).*?op\.execute\((.*?)\)\s*$', migration, re.DOTALL)
if upgrade_func:
    # Find all op.execute calls with triple-quoted strings
    execute_blocks = re.findall(r'op\.execute\(\s*("""[\s\S]*?""")\s*\)', migration)
    for block in execute_blocks:
        # Clean up the SQL string (remove surrounding triple quotes and whitespace)
        sql = block.strip().strip('"').strip()
        cur.execute(sql)
    print("chunking schema applied")

# Now apply indexes (needs documento_fragmento)
sql = Path("infra/sql/005_indexes.sql").read_text(encoding='utf-8')
cur.execute(sql)
print("005_indexes.sql applied")

# Apply pgvector
sql = Path("infra/sql/006_pgvector.sql").read_text(encoding='utf-8')
cur.execute(sql)
print("006_pgvector.sql applied")

# Check tables
cur.execute("""SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name IN
    ('version_articulo', 'documento_fragmento', 'documento_interpretativo', 'norma', 'articulo', 'documento_seccion')
    ORDER BY table_name""")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

# Check embedding columns
for table in ['version_articulo', 'documento_fragmento', 'documento_interpretativo']:
    cur.execute("""SELECT column_name FROM information_schema.columns
        WHERE table_name = %s AND column_name = 'embedding'""", (table,))
    has_emb = cur.fetchone()
    print(f"  {table} embedding: {'yes' if has_emb else 'no'}")

# Counts
for table in ['norma', 'articulo', 'version_articulo', 'documento_fragmento', 'documento_interpretativo']:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"  {table}: {count} rows")

# Check HNSW indexes
cur.execute("""SELECT indexname FROM pg_indexes
    WHERE schemaname = 'public' AND indexname LIKE '%embedding%'""")
indexes = [r[0] for r in cur.fetchall()]
print(f"HNSW indexes: {indexes}")

cur.close()
conn.close()
print("All done!")
