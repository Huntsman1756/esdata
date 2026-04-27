"""Backfill embeddings for all gap tables.

Generates 384-dim embeddings for:
- pgc_cuenta (codigo + descripcion + grupo + nota)
- aeat_modelo (codigo + nombre + impuesto)
- screening_entries (nombre + aliases + categorias + descripcion)
- empresa (nombre + nif)
- norma (codigo + nombre + numero_boe + titulo)
- articulo (numero + titulo + contenido)

Usage:
    python -m scripts.backfill_embeddings [--dry-run] [--batch-size 500]

This is a one-shot backfill script. Future incremental updates
should be handled by source-specific workers.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure apps/api is importable
API_DIR = Path(__file__).resolve().parent.parent / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import text  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s) %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source definitions
# ---------------------------------------------------------------------------

_SOURCES: list[dict[str, Any]] = [
    {
        "table": "pgc_cuenta",
        "id_col": "id",
        "text_cols": ["codigo", "descripcion", "grupo", "nota"],
        "where": "vigente = 1 AND (embedding_384 IS NULL OR content_hash IS NULL)",
    },
    {
        "table": "aeat_modelo",
        "id_col": "id",
        "text_cols": ["codigo", "nombre", "impuesto"],
        "where": "(embedding_384 IS NULL OR content_hash IS NULL)",
    },
    {
        "table": "screening_entries",
        "id_col": "id",
        "text_cols": ["nombre", "aliases", "categorias", "descripcion"],
        "where": "activo = 1 AND (embedding_384 IS NULL OR content_hash IS NULL)",
    },
    {
        "table": "empresa",
        "id_col": "id",
        "text_cols": ["nombre", "nif"],
        "where": "(embedding_384 IS NULL OR content_hash IS NULL)",
    },
    {
        "table": "norma",
        "id_col": "id",
        "text_cols": ["codigo", "nombre", "numero_boe", "titulo"],
        "where": "(embedding_384 IS NULL OR content_hash IS NULL)",
    },
    {
        "table": "articulo",
        "id_col": "id",
        "text_cols": ["numero", "titulo", "contenido"],
        "where": "(embedding_384 IS NULL OR content_hash IS NULL)",
    },
]


def _build_search_text(row: dict, text_cols: list[str]) -> str:
    """Build searchable text from a row dict."""
    parts = []
    for col in text_cols:
        val = row.get(col)
        if val is None:
            continue
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
        elif isinstance(val, list):
            parts.extend(str(v).strip() for v in val if v and str(v).strip())
        elif isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    parts.extend(str(v).strip() for v in parsed if v and str(v).strip())
            except (json.JSONDecodeError, TypeError):
                parts.append(val.strip())
    return " ".join(parts)


def _compute_hash(text: str) -> str:
    """Compute SHA-256 hash of text."""
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def backfill_embeddings(
    batch_size: int = 500,
    dry_run: bool = False,
) -> dict[str, int]:
    """Run embedding backfill across all gap tables.

    Args:
        batch_size: Number of rows to embed per batch.
        dry_run: If True, only report what would be done.

    Returns:
        Dict with counts per table: {table: {"skipped": N, "embedded": N}}
    """
    from db import db_session

    try:
        from apps.workers.embeddings import compute_embedding_hash, embed_texts, get_model_name
    except ImportError:
        logger.error("Cannot import from apps.workers.embeddings — model unavailable")
        return {}

    results: dict[str, int] = {}
    model_name = get_model_name()

    with db_session() as db:
        for source in _SOURCES:
            table = source["table"]
            text_cols = source["text_cols"]
            where = source["where"]
            id_col = source["id_col"]

            # Count rows needing embedding
            count_sql = text(f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}")
            row = db.execute(count_sql).mappings().first()
            total = row["cnt"] if row else 0

            if total == 0:
                logger.info("Table %s: no rows need embedding", table)
                results[table] = {"skipped": 0, "embedded": 0}
                continue

            logger.info("Table %s: %d rows need embedding", table, total)

            # Fetch rows in batches
            batch_num = 0
            embedded = 0
            skipped = 0

            while True:
                batch_sql = text(
                    f"SELECT {id_col}, {', '.join(text_cols)} FROM {table} WHERE {where} LIMIT :limit OFFSET :offset"
                )
                batch_rows = db.execute(
                    batch_sql, {"limit": batch_size, "offset": batch_num * batch_size}
                ).mappings().fetchall()

                if not batch_rows:
                    break

                # Build search texts
                texts = []
                valid_ids = []
                for row in batch_rows:
                    search_text = _build_search_text(dict(row), text_cols)
                    if not search_text.strip():
                        skipped += 1
                        continue
                    texts.append(search_text)
                    valid_ids.append(row[id_col])

                if not texts:
                    continue

                # Generate embeddings
                embeddings = embed_texts(texts, normalize=True)

                if embeddings is None:
                    logger.error("Embedding generation failed for table %s batch %d", table, batch_num)
                    break

                # Update DB
                for row_id, emb, text_content in zip(valid_ids, embeddings, texts):
                    if dry_run:
                        embedded += 1
                        continue

                    content_h = compute_embedding_hash(text_content)
                    # SQLite stores vectors as JSON arrays; PG stores as pgvector
                    emb_str = json.dumps(emb)

                    try:
                        db.execute(
                            text(
                                f"UPDATE {table} "
                                "SET embedding_384 = :emb, "
                                "embedding_model_name = :model, "
                                "content_hash = :hash "
                                "WHERE {id_col} = :rid"
                            ).format(id_col=id_col),
                            {
                                "emb": emb_str,
                                "model": model_name,
                                "hash": content_h,
                                "rid": row_id,
                            },
                        )
                        embedded += 1
                    except Exception:
                        logger.exception("Failed to update row %s in %s", row_id, table)

                batch_num += 1
                logger.info(
                    "Table %s: batch %d — %d embedded, %d skipped",
                    table,
                    batch_num,
                    embedded,
                    skipped,
                )

            results[table] = {"skipped": skipped, "embedded": embedded}

    if dry_run:
        logger.info("=== DRY RUN SUMMARY ===")
        for table, counts in results.items():
            logger.info(
                "  %s: would embed %d rows, skip %d",
                table,
                counts["embedded"],
                counts["skipped"],
            )
    else:
        logger.info("=== BACKFILL COMPLETE ===")
        for table, counts in results.items():
            logger.info(
                "  %s: embedded %d rows, skipped %d",
                table,
                counts["embedded"],
                counts["skipped"],
            )

    return results


def main():
    parser = argparse.ArgumentParser(description="Backfill embeddings for gap tables")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size (default: 500)")
    args = parser.parse_args()

    backfill_embeddings(batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
