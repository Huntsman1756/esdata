import psycopg

conn = psycopg.connect("postgresql://esdata:testpass@localhost:5434/esdata")

# Check id column type
cols = conn.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'version_articulo' 
    AND column_name IN ('id', 'embedding')
""").fetchall()
print("version_articulo id/embedding columns:", cols)

# Check actual IDs
ids = conn.execute("SELECT id, substring(texto, 1, 30) FROM version_articulo LIMIT 5").fetchall()
for row in ids:
    print(f"  id={row[0]} type={type(row[0])} text={row[1]}")

# Check embedding coverage
null_count = conn.execute("SELECT COUNT(*) FROM version_articulo WHERE embedding IS NULL").fetchone()[0]
not_null = conn.execute("SELECT COUNT(*) FROM version_articulo WHERE embedding IS NOT NULL").fetchone()[0]
print(f"\nversion_articulo: {null_count} null, {not_null} with embedding")

# Check documento_interpretativo
cols2 = conn.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'documento_interpretativo' 
    AND column_name IN ('id', 'embedding')
""").fetchall()
print("\ndoc_interpretativo id/embedding columns:", cols2)

ids2 = conn.execute("SELECT id, substring(texto, 1, 30) FROM documento_interpretativo LIMIT 5").fetchall()
for row in ids2:
    print(f"  id={row[0]} type={type(row[0])} text={row[1]}")

# Check documento_fragmento
cols3 = conn.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'documento_fragmento' 
    AND column_name IN ('id', 'embedding')
""").fetchall()
print("\ndoc_fragmento id/embedding columns:", cols3)

# Test update with integer ID
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
emb = model.encode("test", device="cpu", normalize_embeddings=True).tolist()
print(f"\nembedding: len={len(emb)} type={type(emb)}")

# Try update
try:
    conn.execute("UPDATE version_articulo SET embedding = %s WHERE id = %s", (emb, 1))
    r = conn.execute("SELECT embedding IS NOT NULL FROM version_articulo WHERE id = 1").fetchone()[0]
    print(f"Update with integer id=1: embedding set = {r}")
except Exception as e:
    print(f"Update failed: {e}")

conn.close()
