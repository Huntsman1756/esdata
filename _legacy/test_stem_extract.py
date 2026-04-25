import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Check what plainto_tsquery returns as Python string
cur.execute("SELECT plainto_tsquery('spanish', 'Autoliquidación')")
result = cur.fetchone()[0]
print(f"Type: {type(result)}")
print(f"Repr: {repr(result)}")
print(f"Str: {str(result)}")
print(f"Stripped: {str(result).strip(\"'\")}")

# Test: build tsquery string from stems manually
cur.execute("SELECT plainto_tsquery('spanish', 'Autoliquidación')")
stem1 = str(cur.fetchone()[0]).strip("'")
cur.execute("SELECT plainto_tsquery('spanish', 'trimestral')")
stem2 = str(cur.fetchone()[0]).strip("'")
cur.execute("SELECT plainto_tsquery('spanish', 'modelo')")
stem3 = str(cur.fetchone()[0]).strip("'")

tsq = f"'{stem1}' & '{stem2}' & (iva | liv) & '{stem3}' & '303'"
print(f"\nBuilt tsq: {tsq}")

# Test cast
cur.execute(f"SELECT ('{tsq}')::tsquery")
print(f"Cast result: {cur.fetchone()[0]}")

# Test match
cur.execute(f"""
SELECT cf.search_vector @@ ('{tsq}')::tsquery as match_test
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print(f"LIVA art 123 match: {cur.fetchone()[0]}")

# IRPF test
cur.execute("SELECT plainto_tsquery('spanish', 'Declaración')")
stem_d = str(cur.fetchone()[0]).strip("'")
cur.execute("SELECT plainto_tsquery('spanish', 'anual')")
stem_a = str(cur.fetchone()[0]).strip("'")
cur.execute("SELECT plainto_tsquery('spanish', 'modelo')")
stem_m = str(cur.fetchone()[0]).strip("'")

tsq_irpf = f"'{stem_d}' & '{stem_a}' & 'irpf' & '{stem_m}' & '100'"
print(f"\nIRPF tsq: {tsq_irpf}")

cur.execute(f"""
SELECT cf.search_vector @@ ('{tsq_irpf}')::tsquery as match_test
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print(f"IRPF art 124 match: {cur.fetchone()[0]}")

# Check IRPF vector
cur.execute("""
SELECT cf.search_vector FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIRPF') AND numero='124')
LIMIT 1
""")
print(f"IRPF vector: {cur.fetchone()[0]}")

conn.close()
