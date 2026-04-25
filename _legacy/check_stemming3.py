import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Does Spanish stemmer work on ASCII-only words?
cur.execute("SELECT ts_debug('spanish', 'autoliquidacion')")
print(f"ts_debug autoliquidacion: {cur.fetchone()[0]}")

cur.execute("SELECT ts_debug('spanish', 'autoliquidación')")
print(f"ts_debug autoliquidación: {cur.fetchone()[0]}")

# Test with IRPF - ASCII
cur.execute("SELECT ts_debug('spanish', 'irpf')")
print(f"ts_debug irpf: {cur.fetchone()[0]}")

# Test with modelo - ASCII
cur.execute("SELECT ts_debug('spanish', 'modelo')")
print(f"ts_debug modelo: {cur.fetchone()[0]}")

# Test with libros - ASCII
cur.execute("SELECT ts_debug('spanish', 'libros')")
print(f"ts_debug libros: {cur.fetchone()[0]}")

# Check: does to_tsvector reduce 'libro' to 'libr'?
cur.execute("SELECT to_tsvector('spanish', 'libros')")
print(f"to_tsvector libros: {cur.fetchone()[0]}")

# Check: does to_tsvector reduce 'modelo' to 'model'?
cur.execute("SELECT to_tsvector('spanish', 'modelo')")
print(f"to_tsvector modelo: {cur.fetchone()[0]}")

# Check: does to_tsvector reduce 'irpf' to anything?
cur.execute("SELECT to_tsvector('spanish', 'irpf')")
print(f"to_tsvector irpf: {cur.fetchone()[0]}")

# The key insight: Spanish stemmer DOES work on ASCII words!
# 'libros' -> 'libr', 'modelo' -> 'model'
# But 'autoliquidacion' (ASCII) -> 'autoliquidacion' (NOT reduced)

# Why? Let's check the dictionary
cur.execute("SELECT * FROM ts_debug('spanish', 'autoliquidacion')")
row = cur.fetchone()
print(f"\nautoliquidacion full ts_debug: {row}")

cur.execute("SELECT * FROM ts_debug('spanish', 'libros')")
row = cur.fetchone()
print(f"libros full ts_debug: {row}")

# Check if autoliquidacion is in the stopword list or has special handling
cur.execute("SELECT * FROM ts_debug('spanish', 'declaración')")
print(f"declaración: {cur.fetchone()[0]}")

cur.execute("SELECT * FROM ts_debug('spanish', 'declaracion')")
print(f"declaracion: {cur.fetchone()[0]}")

cur.close()
conn.close()
