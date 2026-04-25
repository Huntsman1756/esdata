import os, sys, sqlite3

os.environ['DATABASE_URL'] = 'sqlite:///C:/temp/test_esdata.sqlite3'
sys.path.insert(0, 'apps/api/tests')
import conftest

db_path = str(conftest.engine.url).replace('sqlite:///', '')
conn = sqlite3.connect(db_path)
c = conn.cursor()

print('=== Articulo schema ===')
c.execute("PRAGMA table_info(articulo)")
for row in c.fetchall():
    print(f"  {row}")

print()
print('=== Norma (all) ===')
c.execute("SELECT codigo, titulo FROM norma ORDER BY id")
for row in c.fetchall():
    print(f"  {row[0]} - {row[1]}")

print()
print('=== Articulo (all) ===')
c.execute("SELECT norma_id, numero, tipo FROM articulo ORDER BY id")
for row in c.fetchall():
    print(f"  {row[0]}.{row[1]} [{row[2]}]")

print()
print('=== Search_legislacion function ===')
c.execute("SELECT name FROM sqlite_master WHERE type='function'")
funcs = c.fetchall()
print(f"  Functions: {[r[0] for r in funcs]}")

print()
print('=== Triggers ===')
c.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
triggers = c.fetchall()
print(f"  Triggers: {[r[0] for r in triggers]}")

print()
print('=== All tables ===')
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for row in c.fetchall():
    print(f"  {row[0]}")

conn.close()
