import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test: build tsquery as single string
cur.execute("SELECT ('autoliquidacion & trimestral & iva & model & 303')::tsquery")
print("Single string:", cur.fetchone()[0])

# Test: OR in single string
cur.execute("SELECT ('autoliquidacion & trimestral & (iva | liv) & model & 303')::tsquery")
print("With OR:", cur.fetchone()[0])

# Test: full match
cur.execute("""
SELECT cf.search_vector @@ ('autoliquidacion & trimestral & (iva | liv) & model & 303')::tsquery
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match:", cur.fetchone()[0])

# Check vector
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 vector:", cur.fetchone()[0])

# IRPF - need to test what 'Declaración' stems to
cur.execute("SELECT to_tsvector('spanish', 'Declaración anual irpf modelo 100')")
print("IRPF vec:", cur.fetchone()[0])

# Test IRNR
cur.execute("""
SELECT cf.search_vector @@ ('no & residente & rentas & inmobiliarias & model & 216')::tsquery
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 match:", cur.fetchone()[0])

conn.close()
