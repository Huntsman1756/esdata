#!/usr/bin/env python3
"""Backfill embeddings for all text tables.

Generates vector embeddings for existing text data using sentence-transformers.
Idempotent: skips rows that already have non-null embeddings.

Usage:
    # Dry-run for all tables
    python scripts/data/backfill_embeddings.py --dry-run

    # Backfill legislation articles
    python scripts/data/backfill_embeddings.py --corpus legislacion

    # Backfill doctrine chunks
    python scripts/data/backfill_embeddings.py --corpus doctrina

    # Backfill all tables
    python scripts/data/backfill_embeddings.py --corpus all

    # Limit batch size (default 32)
    python scripts/data/backfill_embeddings.py --batch-size 64

    # Override database URL
    python scripts/data/backfill_embeddings.py --database-url postgresql://...
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

# Import from workers package
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "workers"))
from embeddings import embed_single


def backfill_embeddings(
    engine,
    corpus: str,
    batch_size: int,
    dry_run: bool,
) -> dict[str, int]:
    """Run embedding backfill. Returns counts."""
    counts = {
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    with engine.connect() as conn:
        if corpus in ("legislacion", "all"):
            n = _backfill_version_articulo(conn, batch_size, dry_run, counts)
            counts["processed"] += n
            counts["updated"] += n
            counts["skipped"] += _count_null_embeddings(
                conn, "version_articulo", "embedding"
            )

        if corpus in ("doctrina", "all"):
            n = _backfill_documento_fragmento(conn, batch_size, dry_run, counts)
            counts["processed"] += n
            counts["updated"] += n
            counts["skipped"] += _count_null_embeddings(
                conn, "documento_fragmento", "embedding"
            )

            n2 = _backfill_documento_interpretativo(conn, batch_size, dry_run, counts)
            counts["processed"] += n2
            counts["updated"] += n2

    return counts


def _count_null_embeddings(conn, table: str, column: str) -> int:
    """Count rows with null embedding."""
    try:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
        ).scalar()
        return result or 0
    except Exception:
        return 0


def _backfill_version_articulo(
    conn,
    batch_size: int,
    dry_run: bool,
    counts: dict[str, int],
) -> int:
    """Backfill embeddings for version_articulo.texto."""
    query = text(
        """
        SELECT id, texto
        FROM version_articulo
        WHERE embedding IS NULL AND texto IS NOT NULL AND LENGTH(texto) > 0
        ORDER BY id
        LIMIT 1000
        """
    )

    rows = conn.execute(query).mappings()
    updated = 0
    batch = []

    for row in rows:
        text_data = row["texto"]
        if not text_data or not text_data.strip():
            counts["skipped"] += 1
            continue

        if len(batch) < batch_size:
            batch.append({"id": row["id"], "text": text_data})
            continue

        # Process batch
        _process_batch(conn, "version_articulo", "embedding", batch, dry_run, counts)
        updated += len(batch)
        batch = []

    if batch:
        _process_batch(conn, "version_articulo", "embedding", batch, dry_run, counts)
        updated += len(batch)

    if not dry_run:
        conn.commit()

    return updated


def _backfill_documento_fragmento(
    conn,
    batch_size: int,
    dry_run: bool,
    counts: dict[str, int],
) -> int:
    """Backfill embeddings for documento_fragmento.texto."""
    query = text(
        """
        SELECT id, texto
        FROM documento_fragmento
        WHERE embedding IS NULL AND texto IS NOT NULL AND LENGTH(texto) > 0
        ORDER BY id
        LIMIT 5000
        """
    )

    rows = conn.execute(query).mappings()
    updated = 0
    batch = []

    for row in rows:
        text_data = row["texto"]
        if not text_data or not text_data.strip():
            counts["skipped"] += 1
            continue

        if len(batch) < batch_size:
            batch.append({"id": row["id"], "text": text_data})
            continue

        _process_batch(conn, "documento_fragmento", "embedding", batch, dry_run, counts)
        updated += len(batch)
        batch = []

    if batch:
        _process_batch(conn, "documento_fragmento", "embedding", batch, dry_run, counts)
        updated += len(batch)

    if not dry_run:
        conn.commit()

    return updated


def _backfill_documento_interpretativo(
    conn,
    batch_size: int,
    dry_run: bool,
    counts: dict[str, int],
) -> int:
    """Backfill embeddings for documento_interpretativo.texto."""
    query = text(
        """
        SELECT id, texto
        FROM documento_interpretativo
        WHERE embedding IS NULL AND texto IS NOT NULL AND LENGTH(texto) > 0
        ORDER BY id
        LIMIT 1000
        """
    )

    rows = conn.execute(query).mappings()
    updated = 0
    batch = []

    for row in rows:
        text_data = row["texto"]
        if not text_data or not text_data.strip():
            counts["skipped"] += 1
            continue

        if len(batch) < batch_size:
            batch.append({"id": row["id"], "text": text_data})
            continue

        _process_batch(conn, "documento_interpretativo", "embedding", batch, dry_run, counts)
        updated += len(batch)
        batch = []

    if batch:
        _process_batch(conn, "documento_interpretativo", "embedding", batch, dry_run, counts)
        updated += len(batch)

    if not dry_run:
        conn.commit()

    return updated


def _process_batch(
    conn,
    table: str,
    column: str,
    batch: list[dict[str, Any]],
    dry_run: bool,
    counts: dict[str, int],
) -> None:
    """Process a batch of texts through the embedding model."""
    texts = [item["text"] for item in batch]
    embeddings = embed_single(texts[0]) if len(texts) == 1 else None

    if embeddings is None:
        # Fallback: try batch embed
        from embeddings import embed_texts
        embeddings_list = embed_texts(texts)
        if embeddings_list is None:
            counts["errors"] += len(batch)
            return
        for item, emb in zip(batch, embeddings_list):
            if not dry_run:
                try:
                    conn.execute(
                        text(f"UPDATE {table} SET {column} = :vec WHERE id = :id"),
                        {"vec": emb, "id": item["id"]},
                    )
                except Exception:
                    counts["errors"] += 1
            counts["updated"] += 1
    else:
        # Single text already embedded
        if not dry_run:
            try:
                conn.execute(
                    text(f"UPDATE {table} SET {column} = :vec WHERE id = :id"),
                    {"vec": embeddings, "id": batch[0]["id"]},
                )
            except Exception:
                counts["errors"] += 1
        counts["updated"] += 1


# ── CLI ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill vector embeddings for all text tables."
    )
    parser.add_argument(
        "--corpus",
        choices=["legislacion", "doctrina", "all"],
        default="all",
        help="Which corpus to backfill (default: all).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for embedding (default: 8).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be embedded without writing.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="DATABASE_URL override (default: env var DATABASE_URL).",
    )

    args = parser.parse_args()

    db_url = args.database_url or (
        "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata"
    )

    print(f"Connecting to database...")
    engine = create_engine(db_url, future=True)

    try:
        with engine.connect() as conn:
            tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('version_articulo', 'documento_fragmento', 'documento_interpretativo')"
                )
            ).fetchall()
            table_names = {t[0] for t in tables}
            print(f"Schema OK. Tables found: {', '.join(sorted(table_names))}")

            # Check if embedding columns exist
            for table in ("version_articulo", "documento_fragmento", "documento_interpretativo"):
                if table in table_names:
                    has_col = conn.execute(
                        text(
                            "SELECT COUNT(*) FROM information_schema.columns "
                            "WHERE table_name = :tbl AND column_name = 'embedding'"
                        ),
                        {"tbl": table},
                    ).scalar()
                    if has_col:
                        null_count = _count_null_embeddings(conn, table, "embedding")
                        total = conn.execute(
                            text(f"SELECT COUNT(*) FROM {table}")
                        ).scalar()
                        print(f"  {table}: {null_count}/{total} rows need embeddings")
                    else:
                        print(f"  {table}: NO embedding column (run 006_pgvector.sql first)")

        print(f"\nBackfilling corpus='{args.corpus}' batch_size={args.batch_size} dry_run={args.dry_run}")

        counts = backfill_embeddings(
            engine,
            corpus=args.corpus,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        print()
        print("=== Results ===")
        print(f"  Rows processed:    {counts['processed']}")
        print(f"  Rows updated:      {counts['updated']}")
        print(f"  Rows skipped:      {counts['skipped']}")
        print(f"  Rows with errors:  {counts['errors']}")
        if counts["dry_run"]:
            print("  (dry-run — no data was written)")

        return 0 if counts["errors"] == 0 else 1

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    from pathlib import Path
    raise SystemExit(main())
