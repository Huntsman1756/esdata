import psycopg2
conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

# Check what plainto_tsquery returns
cur.execute("SELECT plainto_tsquery('spanish', 'Autoliquidación')")
result = cur.fetchone()[0]
print(f"Type: {type(result)}")
print(f"Repr: {repr(result)}")
print(f"Str: {str(result)}")

# The result is 'autoliquid' (with quotes as part of the tsquery string representation)
# So I need to strip the outer quotes to get the raw stem
stem = result.strip("'")
print(f"Stem: {stem}")

# Now build tsquery with stems
cur.execute("SELECT plainto_tsquery('spanish', 'trimestral')")
stem2 = cur.fetchone()[0].strip("'")
print(f"Stem2: {stem2}")

cur.execute("SELECT plainto_tsquery('spanish', 'modelo')")
stem3 = cur.fetchone()[0].strip("'")
print(f"Stem3: {stem3}")

# Build: 'autoliquid' & 'trimestral' & (iva | liv) & 'model' & '303'
tsq = f"'{stem}' & '{stem2}' & (iva | liv) & '{stem3}' & '303'"
print(f"Built: {tsq}")

# Test match
cur.execute(f"""
SELECT cf.search_vector @@ ('{tsq}')::tsquery
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print(f"LIVA match: {cur.fetchone()[0]}")

# Check vector
cur.execute("""
SELECT cf.search_vector FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
LIMIT 1
""")
print(f"LIVA vector: {cur.fetchone()[0]}")

conn.close()
