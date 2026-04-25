import psycopg2, os
conn = psycopg2.connect(dsn=os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check if 'contractor' or 'digital' exist in IRNR chunks
cur.execute("""
SELECT da.numero, substr(da.texto, 1, 200)
FROM documento_fragmento da
WHERE da.norma_id = 46
  AND (da.texto ILIKE '%contractor%' OR da.texto ILIKE '%digital%' OR da.texto ILIKE '%americano%')
LIMIT 10
""")
print('=== Contractor/digital in IRNR chunks ===')
for r in cur.fetchall():
    print(f'  Art.{r[0]}: {r[1]}...')

# Check version_articulo for these terms
cur.execute("""
SELECT numero, substr(texto, 1, 200)
FROM version_articulo
WHERE version_id IN (SELECT id FROM version WHERE norma_id = 46)
  AND (texto ILIKE '%contractor%' OR texto ILIKE '%digital%' OR texto ILIKE '%americano%' OR texto ILIKE '%proveedor%')
LIMIT 10
""")
print()
print('=== Contractor/digital in version_articulo ===')
for r in cur.fetchall():
    print(f'  Art.{r[0]}: {r[1]}...')

# Check what IRNR articles actually exist
cur.execute("""
SELECT COUNT(*) FROM version_articulo va
JOIN version v ON v.id = va.version_id
WHERE v.norma_id = 46
""")
print(f'\nTotal IRNR articles in version_articulo: {cur.fetchone()[0]}')

# Check what chunks exist for IRNR
cur.execute("SELECT COUNT(*) FROM documento_fragmento WHERE norma_id = 46")
print(f'Total IRNR chunks: {cur.fetchone()[0]}')

# Check what IRNR chunks contain (sample)
cur.execute("""
SELECT da.numero, substr(da.texto, 1, 300)
FROM documento_fragmento da
WHERE da.norma_id = 46
ORDER BY da.numero
LIMIT 5
""")
print('\n=== Sample IRNR chunks ===')
for r in cur.fetchall():
    print(f'  Art.{r[0]}: {r[1]}...')

cur.close()
conn.close()
