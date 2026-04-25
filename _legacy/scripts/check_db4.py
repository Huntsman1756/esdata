import os, sys, sqlite3

os.environ['DATABASE_URL'] = 'sqlite:///C:/temp/test_esdata.sqlite3'
sys.path.insert(0, 'apps/api/tests')
import conftest

db_path = str(conftest.engine.url).replace('sqlite:///', '')
conn = sqlite3.connect(db_path)
c = conn.cursor()

print('=== Version_articulo schema ===')
c.execute("PRAGMA table_info(version_articulo)")
for row in c.fetchall():
    print(f"  {row}")

print()
print('=== Version_articulo (all) ===')
c.execute("SELECT articulo_id, substr(texto,1,80), vigente_desde, vigente_hasta FROM version_articulo ORDER BY id")
for row in c.fetchall():
    print(f"  art_id={row[0]} | desde={row[2]} hasta={row[3]}")
    print(f"    texto: {row[1]}...")

print()
print('=== Documento_fragmento schema ===')
c.execute("PRAGMA table_info(documento_fragmento)")
for row in c.fetchall():
    print(f"  {row}")

print()
print('=== Documento_fragmento (count) ===')
c.execute("SELECT COUNT(*) FROM documento_fragmento")
print(f"  {c.fetchone()[0]} rows")

conn.close()
