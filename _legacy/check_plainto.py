import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Test different tsquery functions
cur.execute("SELECT plainto_tsquery('spanish', 'autoliquidacion')")
print(f"plainto_tsquery('autoliquidacion'): {cur.fetchone()[0]}")

cur.execute("SELECT plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"plainto_tsquery('IRPF modelo 100'): {cur.fetchone()[0]}")

cur.execute("SELECT plainto_tsquery('spanish', 'IVA libros')")
print(f"plainto_tsquery('IVA libros'): {cur.fetchone()[0]}")

# Test matching
cur.execute("SELECT to_tsvector('spanish', 'autoliquidación es el procedimiento') @@ plainto_tsquery('spanish', 'autoliquidacion')")
print(f"autoliquidacion match with plainto_tsquery: {cur.fetchone()[0]}")

cur.execute("SELECT to_tsvector('spanish', 'El contribuyente que obtenga rendimientos del trabajo estará obligado a presentar la declaración de la renta correspondiente al ejercicio mediante el modelo 100') @@ plainto_tsquery('spanish', 'IRPF modelo 100')")
print(f"IRPF modelo 100 match with plainto_tsquery: {cur.fetchone()[0]}")

# Check search_vector match
cur.execute("SELECT search_vector @@ plainto_tsquery('spanish', 'autoliquidacion') FROM version_articulo WHERE texto LIKE '%autoliquidación%' LIMIT 1")
print(f"search_vector autoliquidacion match: {cur.fetchone()[0]}")

cur.close()
conn.close()
