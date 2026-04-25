import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Approach: get stems via plainto_tsquery, then build tsquery string manually
# Step 1: Get individual stems
cur.execute("SELECT plainto_tsquery('spanish', 'Autoliquidación')")
stem1 = cur.fetchone()[0]
print("stem autoliquidación:", stem1)

cur.execute("SELECT plainto_tsquery('spanish', 'trimestral')")
stem2 = cur.fetchone()[0]
print("stem trimestral:", stem2)

cur.execute("SELECT plainto_tsquery('spanish', 'modelo')")
stem3 = cur.fetchone()[0]
print("stem modelo:", stem3)

# Step 2: Build tsquery string from stems + OR for abbreviations
# For iva: we need (iva | liv)
# The string approach: 'autoliquid' & 'trimestral' & (iva | liv) & 'model' & '303'
tsq_str = f"{stem1} & {stem2} & (iva | liv) & {stem3} & '303'"
print("tsq string:", tsq_str)

# Step 3: Cast to tsquery and test
cur.execute(f"SELECT ('{tsq_str}')::tsquery")
print("cast tsquery:", cur.fetchone()[0])

# Step 4: Match
cur.execute(f"""
SELECT cf.search_vector @@ ('{tsq_str}')::tsquery
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print("LIVA art 123 match:", cur.fetchone()[0])

# IRPF test
cur.execute("SELECT plainto_tsquery('spanish', 'Declaración')")
stem_d = cur.fetchone()[0]
cur.execute("SELECT plainto_tsquery('spanish', 'anual')")
stem_a = cur.fetchone()[0]
cur.execute("SELECT plainto_tsquery('spanish', 'modelo')")
stem_m = cur.fetchone()[0]

tsq_irpf = f"'{stem_d}' & '{stem_a}' & 'irpf' & '{stem_m}' & '100'"
print("tsq IRPF:", tsq_irpf)

cur.execute(f"""
SELECT cf.search_vector @@ ('{tsq_irpf}')::tsquery
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

conn.close()
