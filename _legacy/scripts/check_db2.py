import os, sys, sqlite3

os.environ['DATABASE_URL'] = 'sqlite:///C:/temp/test_esdata.sqlite3'
sys.path.insert(0, 'apps/api/tests')
import conftest

db_path = str(conftest.engine.url).replace('sqlite:///', '')
conn = sqlite3.connect(db_path)
c = conn.cursor()

print('=== Norma (top 5) ===')
c.execute("SELECT codigo, titulo FROM norma ORDER BY id LIMIT 5")
for row in c.fetchall():
    print(f"  {row[0]} - {row[1]}")

print()
print('=== Articulo (top 5) ===')
c.execute("SELECT norma_id, numero, tipo, substr(texto,1,60) FROM articulo ORDER BY id LIMIT 5")
for row in c.fetchall():
    print(f"  {row[0]}.{row[1]} [{row[2]}]: {row[3]}")

print()
print('=== Documento_interpretativo (all) ===')
c.execute("SELECT tipo_documento, referencia, organismo_emisor, substr(texto,1,80) FROM documento_interpretativo ORDER BY id")
for row in c.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]}")
    print(f"    {row[3]}...")

print()
print('=== Modelo_articulo ===')
c.execute("SELECT modelo_id, articulo_id FROM modelo_articulo")
for row in c.fetchall():
    print(f"  modelo={row[0]} articulo={row[1]}")

print()
print('=== Modelo_normativa ===')
c.execute("SELECT modelo_id, norma_id, articulo_referencia FROM modelo_normativa")
for row in c.fetchall():
    print(f"  modelo={row[0]} norma={row[1]} art={row[2]}")

print()
print('=== Obligation regulatoria ===')
c.execute("SELECT codigo, nombre, fuente FROM obligacion_regulatoria")
for row in c.fetchall():
    print(f"  {row[0]} - {row[1]} - {row[2]}")

print()
print('=== Buscar todas las tablas con "legisl" ===')
c.execute("SELECT name FROM sqlite_master WHERE name LIKE '%legisl%'")
r = c.fetchall()
print(f"  {r if r else 'NONE'}")

print()
print('=== Buscar tabla con "search" o "fts" ===')
c.execute("SELECT name FROM sqlite_master WHERE name LIKE '%search%' OR name LIKE '%fts%' OR name LIKE '%full%'")
r = c.fetchall()
print(f"  {r if r else 'NONE'}")

conn.close()
