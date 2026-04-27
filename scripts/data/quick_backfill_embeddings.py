#!/usr/bin/env python3
"""Backfill embeddings - runs inside API container."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "workers"))

from sqlalchemy import create_engine, text
from embeddings import embed_single, embed_texts

DB_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@postgres:5432/esdata")

def count_null(conn, table, column):
    try:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")).scalar() or 0
    except Exception:
        return 0

def process_batch(conn, table, column, batch, dry_run):
    texts = [item["text"] for item in batch]
    embeddings = None
    if len(texts) == 1:
        embeddings = embed_single(texts[0])
    else:
        embeddings_list = embed_texts(texts)
        if embeddings_list:
            for item, emb in zip(batch, embeddings_list):
                if not dry_run:
                    try:
                        conn.execute(
                            text(f"UPDATE {table} SET {column} = :vec WHERE id = :id"),
                            {"vec": emb, "id": item["id"]},
                        )
                    except Exception as e:
                        print(f"  ERROR updating {item['id']}: {e}")
                print(f"  Updated {item['id']}")
            return len(embeddings_list)
    
    if embeddings is None:
        return 0
    
    if not dry_run:
        try:
            conn.execute(
                text(f"UPDATE {table} SET {column} = :vec WHERE id = :id"),
                {"vec": embeddings, "id": batch[0]["id"]},
            )
        except Exception as e:
            print(f"  ERROR updating {batch[0]['id']}: {e}")
    print(f"  Updated {batch[0]['id']}")
    return 1

def backfill_table(conn, table, column, limit, batch_size, dry_run, description):
    print(f"\n=== {description} ({table}) ===")
    null_count = count_null(conn, table, column)
    total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
    print(f"  Total rows: {total}, Need embeddings: {null_count}")
    
    query = text(f"""
        SELECT id, texto FROM {table}
        WHERE {column} IS NULL AND texto IS NOT NULL AND LENGTH(texto) > 0
        ORDER BY id LIMIT :limit
    """)
    
    rows = conn.execute(query, {"limit": limit}).mappings()
    batch = []
    updated = 0
    skipped = 0
    
    for row in rows:
        text_data = row["texto"]
        if not text_data or not text_data.strip():
            skipped += 1
            continue
        batch.append({"id": row["id"], "text": text_data})
        if len(batch) >= batch_size:
            updated += process_batch(conn, table, column, batch, dry_run)
            batch = []
    
    if batch:
        updated += process_batch(conn, table, column, batch, dry_run)
    
    if not dry_run:
        conn.commit()
    
    print(f"  Updated: {updated}, Skipped: {skipped}")
    return updated, skipped

def main():
    print(f"Connecting to: {DB_URL}")
    engine = create_engine(DB_URL, future=True)
    
    with engine.connect() as conn:
        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN "
            "('version_articulo', 'documento_fragmento', 'documento_interpretativo')"
        )).fetchall()
        table_names = {t[0] for t in tables}
        print(f"Tables found: {', '.join(sorted(table_names))}")
        
        for table in ("version_articulo", "documento_fragmento", "documento_interpretativo"):
            if table in table_names:
                has_col = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_name = :tbl AND column_name = 'embedding'"
                ), {"tbl": table}).scalar()
                if has_col:
                    print(f"  {table}: has embedding column")
                else:
                    print(f"  {table}: NO embedding column - skipping")
        
        dry_run = "--dry-run" in sys.argv
        batch_size = 4
        
        # Check which tables actually have embedding columns
        tables_with_embedding = set()
        for table in table_names:
            has_col = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = :tbl AND column_name = 'embedding'"
            ), {"tbl": table}).scalar()
            if has_col:
                tables_with_embedding.add(table)
        
        print(f"\nTables with embedding column: {', '.join(sorted(tables_with_embedding))}")
        
        total_updated = 0
        total_skipped = 0
        
        if "legislacion" in sys.argv or "all" in sys.argv:
            if "version_articulo" in tables_with_embedding:
                u, s = backfill_table(conn, "version_articulo", "embedding", 1000, batch_size, dry_run, "Legislacion")
                total_updated += u
                total_skipped += s
            else:
                print("\n=== Legislacion (version_articulo) ===")
                print("  SKIPPED: no embedding column")
        
        if "doctrina" in sys.argv or "all" in sys.argv:
            if "documento_fragmento" in tables_with_embedding:
                u, s = backfill_table(conn, "documento_fragmento", "embedding", 5000, batch_size, dry_run, "Doctrina chunks")
                total_updated += u
                total_skipped += s
            else:
                print("\n=== Doctrina chunks (documento_fragmento) ===")
                print("  SKIPPED: no embedding column")
            
            if "documento_interpretativo" in tables_with_embedding:
                u, s = backfill_table(conn, "documento_interpretativo", "embedding", 1000, batch_size, dry_run, "Doctrina docs")
                total_updated += u
                total_skipped += s
            else:
                print("\n=== Doctrina docs (documento_interpretativo) ===")
                print("  SKIPPED: no embedding column")
    
    print(f"\n=== TOTALS ===")
    print(f"  Updated: {total_updated}")
    print(f"  Skipped: {total_skipped}")
    if dry_run:
        print("  (dry-run)")
    engine.dispose()

if __name__ == "__main__":
    main()
