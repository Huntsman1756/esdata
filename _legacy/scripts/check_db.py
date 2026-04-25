import sqlite3
db = sqlite3.connect('G:/_Proyectos/esdata/apps/api/tests/test_esdata.sqlite3')
c = db.cursor()

print('=== Tablas ===')
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for r in c.fetchall(): print('  ' + r[0])

print()
print('=== Norma ===')
c.execute('SELECT COUNT(*) FROM norma')
print('  Count: ' + str(c.fetchone()[0]))

print()
print('=== Articulo ===')
c.execute('PRAGMA table_info(articulo)')
cols = [r[1] for r in c.fetchall()]
print('  Columns: ' + str(cols))
c.execute('SELECT COUNT(*) FROM articulo')
print('  Count: ' + str(c.fetchone()[0]))

print()
print('=== Version_articulo ===')
c.execute('SELECT COUNT(*) FROM version_articulo')
print('  Count: ' + str(c.fetchone()[0]))
c.execute('SELECT n.codigo, a.numero, substr(va.texto,1,80) FROM version_articulo va JOIN articulo a ON a.id=va.articulo_id JOIN norma n ON n.id=a.norma_id LIMIT 3')
for r in c.fetchall(): print('  ' + r[0] + '.' + r[1] + ': ' + r[2][:80] + '...')

print()
print('=== Documento_interpretativo ===')
c.execute('SELECT COUNT(*) FROM documento_interpretativo')
print('  Count: ' + str(c.fetchone()[0]))
c.execute('SELECT tipo_documento, referencia, substr(texto,1,80) FROM documento_interpretativo LIMIT 3')
for r in c.fetchall(): print('  ' + r[0] + ' | ' + r[1] + ' | ' + r[2][:80] + '...')

print()
print('=== Documento_fragmento (chunks) ===')
c.execute('SELECT COUNT(*) FROM documento_fragmento')
print('  Count: ' + str(c.fetchone()[0]))

print()
print('=== Busqueda_fts ===')
try:
    c.execute('SELECT COUNT(*) FROM busqueda_fts')
    print('  Count: ' + str(c.fetchone()[0]))
except Exception as e:
    print('  Table does not exist: ' + str(e))

db.close()
