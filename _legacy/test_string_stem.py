import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test: string cast stemma?
cur.execute("SELECT ('modelo')::tsquery")
print("'modelo'::tsquery:", cur.fetchone()[0])

cur.execute("SELECT ('autoliquidación')::tsquery")
print("'autoliquidación'::tsquery:", cur.fetchone()[0])

# Test: full query with accented terms
cur.execute("""
SELECT cf.search_vector @@ ('autoliquidación & trimestral & (iva | liv) & modelo & 303')::tsquery
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match (accented):", cur.fetchone()[0])

# Test: IRPF
cur.execute("""
SELECT cf.search_vector @@ ('declaración & anual & irpf & modelo & 100')::tsquery
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print("IRPF art 124 match:", cur.fetchone()[0])

# Check IRPF vector
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print("IRPF art 124 vector:", cur.fetchone()[0])

# Test: IRNR
cur.execute("""
SELECT cf.search_vector @@ ('no & residente & rentas & inmobiliarias & (irnr | noresident) & modelo & 216')::tsquery
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 match:", cur.fetchone()[0])

# Check IRNR vector
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 vector:", cur.fetchone()[0])

conn.close()
