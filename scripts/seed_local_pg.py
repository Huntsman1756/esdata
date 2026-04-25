"""Seed the local pgvector container with test data from conftest."""
import psycopg2
from pathlib import Path

DB_URL = "postgresql://esdata:testpass@localhost:5434/esdata"

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

# Extract schema + seed from conftest
conftest = Path("apps/api/tests/conftest.py").read_text(encoding='utf-8')

# Find all triple-quoted SQL strings
import re
statements = re.findall(r'"""(?:\s*\n)?([\s\S]*?)"""(?:\s*,\s*)?\s*""', conftest)

# Also handle single-line triple-quoted strings in the STATEMENTS list
# The STATEMENTS list uses """ at start and end of each string
all_sql = re.findall(r'"""([\s\S]*?)"""', conftest)

# Filter out empty or non-SQL
sql_statements = []
for s in all_sql:
    stripped = s.strip()
    if stripped and any(kw in stripped.upper() for kw in ['CREATE', 'INSERT', 'SELECT']):
        sql_statements.append(stripped)

print(f"Found {len(sql_statements)} SQL statements")

# Apply them
applied = 0
errors = []
for i, sql in enumerate(sql_statements):
    try:
        cur.execute(sql)
        applied += 1
    except Exception as e:
        # Some statements may fail if dependencies don't exist yet
        # (e.g., FK references to tables not yet created)
        if i < 20:  # First 20 should be CREATE TABLE
            errors.append((i, sql[:80], str(e)[:100]))

print(f"Applied: {applied}, Errors: {len(errors)}")
if errors:
    for idx, sql_preview, err in errors:
        print(f"  [{idx}] {sql_preview}... -> {err}")

# Check counts
for table in ['norma', 'articulo', 'version_articulo', 'documento_fragmento', 'documento_interpretativo', 'materia', 'aeat_modelo']:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")
    except Exception as e:
        print(f"  {table}: error - {e}")

cur.close()
conn.close()
print("Done!")
