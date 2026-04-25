"""Generate chunks from version_articulo for the local PG container."""
import psycopg2
from pathlib import Path

DB_URL = "postgresql://esdata:testpass@localhost:5434/esdata"

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

# Get all articles with their latest versions
cur.execute("""
    SELECT va.id, va.articulo_id, va.texto, n.codigo, a.numero
    FROM version_articulo va
    JOIN articulo a ON a.id = va.articulo_id
    JOIN norma n ON n.id = a.norma_id
    WHERE va.vigente_desde = (
        SELECT MAX(v2.vigente_desde)
        FROM version_articulo v2
        WHERE v2.articulo_id = va.articulo_id
    )
    AND va.texto IS NOT NULL AND LENGTH(va.texto) > 0
    ORDER BY n.codigo, a.numero
""")
rows = cur.fetchall()
print(f"Found {len(rows)} articles to chunk")

chunk_index = 0
for va_id, art_id, texto, codigo, numero in rows:
    # Split text into chunks of ~500 chars
    text = texto.strip()
    chunk_size = 500
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    for ci, chunk_text in enumerate(chunks):
        if not chunk_text.strip():
            continue
        chunk_index += 1
        try:
            cur.execute("""
                INSERT INTO documento_fragmento
                    (documento_origen_tipo, documento_origen_id, chunk_index, chunk_type, titulo, texto)
                VALUES ('legislacion', %s, %s, 'natural', %s, %s)
            """, (art_id, ci, f"{codigo} {numero}", chunk_text))
        except Exception as e:
            print(f"  Error chunking {codigo} {numero}: {e}")

print(f"Created {chunk_index} chunks")

# Count
cur.execute("SELECT COUNT(*) FROM documento_fragmento")
print(f"Total documento_fragmento: {cur.fetchone()[0]}")

# Check embedding columns exist
for table in ['version_articulo', 'documento_fragmento']:
    cur.execute("""SELECT column_name FROM information_schema.columns
        WHERE table_name = %s AND column_name = 'embedding'""", (table,))
    has_emb = cur.fetchone()
    print(f"  {table} embedding: {'yes' if has_emb else 'no'}")

cur.close()
conn.close()
print("Done!")
