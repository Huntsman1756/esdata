import psycopg2

conn = psycopg2.connect("dbname=esdata user=esdata password=testpass host=localhost port=5434")
cur = conn.cursor()

# Verificar qué genera plainto_tsquery para cada término
terms = ['autoliquidacion', 'trimestral', 'iva', 'liv', 'modelo', 'model', '303', 'irnr', 'noresident']
for t in terms:
    cur.execute("SELECT plainto_tsquery('spanish', %s)", (t,))
    print(f"plainto_tsquery('{t}'):", cur.fetchone()[0])

print()

# Verificar qué genera websearch_to_tsquery con términos separados por espacio
cur.execute("SELECT websearch_to_tsquery('spanish', 'autoliquidacion trimestral iva modelo 303')")
print("websearch:", cur.fetchone()[0])

# Verificar si 'iva | liv' funciona como tsquery literal
cur.execute("SELECT 'liv'::tsquery")
print("'liv'::tsquery:", cur.fetchone()[0])

# Verificar si puedo construir un tsquery con |
cur.execute("""
SELECT to_tsvector('spanish', 'LIVA autoliquidacion modelo 303') @@ ('autoliquidacion' & 'liv' & 'model' & '303') as match_liv
""")
print("Match con 'liv' (AND):", cur.fetchone()[0])

cur.execute("""
SELECT to_tsvector('spanish', 'LIVA autoliquidacion modelo 303') @@ ('autoliquidacion' & 'iva' & 'model' & '303') as match_iva
""")
print("Match con 'iva' (AND):", cur.fetchone()[0])

cur.close()
conn.close()
