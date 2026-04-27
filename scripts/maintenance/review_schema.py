import psycopg2
conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata', options='-c search_path=public')
cur = conn.cursor()
for table in ['norma', 'articulo', 'version_articulo', 'documento_fragmento']:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", (table,))
    print(f'\n=== {table} ===')
    for row in cur.fetchall():
        print(f'  {row[0]:30s} {row[1]}')
conn.close()
