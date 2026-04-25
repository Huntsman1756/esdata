import psycopg2
import psycopg2.extras
import sys
import os

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "esdata",
    "user": "esdata",
    "password": "esdata_dev",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def check_tables(conn):
    """Check which tables exist and have embedding columns."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name IN ('version_articulo', 'documento_fragmento', 'documento_interpretativo')
            AND column_name IN ('embedding', 'texto')
            ORDER BY table_name, column_name
        """)
        rows = cur.fetchall()
    
    tables = {}
    for table_name, col in rows:
        if table_name not in tables:
            tables[table_name] = {"has_embedding": False, "has_texto": False}
        if col == "embedding":
            tables[table_name]["has_embedding"] = True
        if col == "texto":
            tables[table_name]["has_texto"] = True
    
    for tname in sorted(tables.keys()):
        t = tables[tname]
        emb = "YES" if t["has_embedding"] else "NO"
        txt = "YES" if t["has_texto"] else "NO"
        print(f"  {tname}: embedding={emb}, texto={txt}")
    
    return tables

def count_rows(conn, table):
    """Count total and null embedding rows."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        total = cur.fetchone()[0]
        
        if total == 0:
            return 0, 0
        
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE embedding IS NULL")
        null_count = cur.fetchone()[0]
    
    return total, null_count

def backfill_table(conn, table, batch_size=16, dry_run=False):
    """Backfill embeddings for a single table."""
    print(f"\n=== {table} ===")
    
    total, null_count = count_rows(conn, table)
    print(f"  Total: {total}, Need embeddings: {null_count}")
    
    if null_count == 0:
        print("  Already done - skipping")
        return 0, 0
    
    # Get rows without embeddings
    with conn.cursor(name="backfill_cursor", cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.itersize = batch_size * 2
        cur.execute("""
            SELECT id, texto FROM {}
            WHERE embedding IS NULL AND texto IS NOT NULL AND LENGTH(texto) > 0
            ORDER BY id
            LIMIT %s
        """.format(table), (null_count,))
        
        updated = 0
        skipped = 0
        batch = []
        
        for row in cur:
            texto = row["texto"]
            if not texto or not str(texto).strip():
                skipped += 1
                continue
            
            # For now, just count - actual embedding requires sentence-transformers
            batch.append({
                "id": row["id"],
                "text_preview": str(texto)[:80],
            })
            
            if len(batch) >= batch_size:
                print(f"  Batch of {len(batch)} ready for embedding")
                if not dry_run:
                    # Would update here
                    pass
                updated += len(batch)
                batch = []
        
        if batch:
            print(f"  Final batch of {len(batch)} ready for embedding")
            if not dry_run:
                pass
            updated += len(batch)
    
    print(f"  Rows to embed: {updated}, Skipped: {skipped}")
    return updated, skipped

def main():
    dry_run = "--dry-run" in sys.argv
    
    print(f"Connecting to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
    conn = get_connection()
    print("Connected OK")
    
    print("\n--- Schema check ---")
    tables = check_tables(conn)
    
    print("\n--- Row counts ---")
    for table in tables:
        total, null_count = count_rows(conn, table)
        print(f"  {table}: {total} total, {null_count} need embeddings")
    
    if dry_run:
        print("\n=== DRY RUN MODE ===")
        for table in tables:
            if tables[table]["has_embedding"]:
                backfill_table(conn, table, dry_run=True)
    else:
        print("\n=== BACKFILL MODE ===")
        print("NOTE: Actual embedding generation requires sentence-transformers.")
        print("This mode only counts rows that need embedding.")
        for table in tables:
            if tables[table]["has_embedding"]:
                backfill_table(conn, table, dry_run=False)
    
    conn.close()
    print("\nDone.")

if __name__ == "__main__":
    main()
