import psycopg2, os
conn = psycopg2.connect(dsn=os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT id, codigo FROM norma WHERE codigo IN (\'IRNR\', \'LIRNR\')')
for r in cur.fetchall():
    print('id=%s codigo=%s' % r)
cur.close()
conn.close()
