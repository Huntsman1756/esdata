import psycopg2
conn = psycopg2.connect("host=localhost port=5432 dbname=esdata user=esdata password=esdata_dev")
cur = conn.cursor()
cur.execute("SELECT 1")
print(cur.fetchone())
cur.close()
conn.close()
print("psycopg2 OK")
