"""Shared change detection for incremental worker reindexing.

Detects remote content changes by SHA-256 hash, etag, or last-modified.
Skips sync for unchanged entities; invalidates old embeddings on change.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceChange:
    """Result of a change detection check."""

    changed: bool
    old_hash: str | None = None
    new_hash: str | None = None
    etag: str | None = None
    last_modified: str | None = None


def compute_content_hash(content: str | bytes) -> str:
    """Compute SHA-256 hex digest of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def ensure_source_revision_table(conn: Connection) -> None:
    """Create source_revision table if it doesn't exist (idempotent)."""
    dialect_name = conn.engine.dialect.name
    if dialect_name == "sqlite":
        ddl = """
            CREATE TABLE IF NOT EXISTS source_revision (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_name TEXT NOT NULL,
                source_entity_tipo TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                content_hash_sha256 TEXT NOT NULL,
                etag TEXT,
                last_modified TEXT,
                content_length INTEGER,
                fetched_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                UNIQUE(worker_name, source_entity_tipo, source_entity_id)
            )
        """
        default_ts = "datetime('now')"
    else:
        ddl = """
            CREATE TABLE IF NOT EXISTS source_revision (
                id SERIAL PRIMARY KEY,
                worker_name TEXT NOT NULL,
                source_entity_tipo TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                content_hash_sha256 TEXT NOT NULL,
                etag TEXT,
                last_modified TEXT,
                content_length INTEGER,
                fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(worker_name, source_entity_tipo, source_entity_id)
            )
        """
        default_ts = "now()"

    conn.execute(text(ddl))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_source_revision_worker_entity
            ON source_revision(worker_name, source_entity_tipo, source_entity_id)
    """))


def check_content_changed(
    conn: Connection,
    worker_name: str,
    source_entity_tipo: str,
    source_entity_id: str,
    content: str | bytes,
    etag: str | None = None,
    last_modified: str | None = None,
) -> SourceChange:
    """Check if remote content has changed since last sync.

    Primary: SHA-256 hash comparison.
    Fallback: etag comparison, then last-modified.

    If content is unchanged, returns changed=False and does NOT update
    the stored revision (avoiding unnecessary writes).
    """
    new_hash = compute_content_hash(content)

    row = conn.execute(
        text("""
            SELECT content_hash_sha256, etag, last_modified
            FROM source_revision
            WHERE worker_name = :worker
              AND source_entity_tipo = :tipo
              AND source_entity_id = :entity_id
        """),
        {"worker": worker_name, "tipo": source_entity_tipo, "entity_id": source_entity_id},
    ).fetchone()

    if row is None:
        return SourceChange(changed=True, new_hash=new_hash, etag=etag, last_modified=last_modified)

    old_hash = row[0]
    old_etag = row[1]
    old_lm = row[2]

    if new_hash == old_hash:
        return SourceChange(changed=False, old_hash=old_hash)

    return SourceChange(
        changed=True,
        old_hash=old_hash,
        new_hash=new_hash,
        etag=etag,
        last_modified=last_modified,
    )


def record_revision(
    conn: Connection,
    worker_name: str,
    source_entity_tipo: str,
    source_entity_id: str,
    content: str | bytes,
    etag: str | None = None,
    last_modified: str | None = None,
) -> None:
    """Record a revision after processing content. Upserts atomically."""
    new_hash = compute_content_hash(content)
    content_length = len(content) if isinstance(content, str) else len(content.encode("utf-8"))
    dialect_name = conn.engine.dialect.name
    ts_func = "datetime('now')" if dialect_name == "sqlite" else "now()"

    conn.execute(text("""
        INSERT INTO source_revision (
            worker_name, source_entity_tipo, source_entity_id,
            content_hash_sha256, etag, last_modified, content_length
        ) VALUES (:worker, :tipo, :entity_id, :hash, :etag, :lm, :length)
        ON CONFLICT (worker_name, source_entity_tipo, source_entity_id)
        DO UPDATE SET
            content_hash_sha256 = EXCLUDED.content_hash_sha256,
            etag = EXCLUDED.etag,
            last_modified = EXCLUDED.last_modified,
            content_length = EXCLUDED.content_length,
            fetched_at = :ts
    """), {
        "worker": worker_name,
        "tipo": source_entity_tipo,
        "entity_id": source_entity_id,
        "hash": new_hash,
        "etag": etag,
        "lm": last_modified,
        "length": content_length,
        "ts": ts_func,
    })


def invalidate_old_embeddings(
    conn: Connection,
    source_entity_id: str,
) -> int:
    """Invalidate (NULL) old embeddings for entities whose content changed.

    Returns count of invalidated rows.
    """
    # Count rows that will be invalidated before updating.
    # This works on both SQLite and PostgreSQL and avoids the
    # RETURNING/rowcount differences between dialects.
    count = conn.execute(
        text("""
            SELECT COUNT(*) FROM version_articulo
            WHERE boe_bloque_id = :block_id
              AND embedding IS NOT NULL
        """),
        {"block_id": source_entity_id},
    ).scalar()

    if count > 0:
        conn.execute(
            text("""
                UPDATE version_articulo
                SET embedding = NULL
                WHERE boe_bloque_id = :block_id
                  AND embedding IS NOT NULL
            """),
            {"block_id": source_entity_id},
        )

    return count
