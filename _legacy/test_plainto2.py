import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Test: plainto_tsquery con (iva | liv) - SÍ stemma y SÍ hace OR
cur.execute("SELECT plainto_tsquery('spanish', 'autoliquidación trimestral (iva | liv) modelo 303')")
print("plainto with OR:", cur.fetchone()[0])

# Test: match
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'autoliquidación trimestral (iva | liv) modelo 303')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match:", cur.fetchone()[0])

# Test: IRPF con (irpf)
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'declaración anual irpf modelo 100')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print("IRPF art 124 match:", cur.fetchone()[0])

# Test: IRNR con (irnr | noresident)
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'no residente rentas inmobiliarias (irnr | noresident) modelo 216')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRNR') AND numero='123')
LIMIT 1
""")
print("IRNR art 123 match:", cur.fetchone()[0])

# Test: DAC6 con (dac6 | transfronteriz)
cur.execute("""
SELECT cf.search_vector @@ plainto_tsquery('spanish', 'mecanismos transfronterizos (dac6 | transfronteriz)')
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='DAC6') AND numero='1')
LIMIT 1
""")
print("DAC6 match:", cur.fetchone()[0])

# Check DAC6 vector
cur.execute("""
SELECT cf.search_vector
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='DAC6') AND numero='1')
LIMIT 1
""")
print("DAC6 vector:", cur.fetchone()[0])

conn.close()
