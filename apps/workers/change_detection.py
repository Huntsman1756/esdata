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


def _source_revision_columns(conn: Connection) -> set[str]:
    dialect_name = conn.engine.dialect.name
    if dialect_name == "sqlite":
        rows = conn.execute(text("PRAGMA table_info(source_revision)"))
        return {row[1] for row in rows}

    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'source_revision'
            """
        )
    )
    return {row[0] for row in rows}


def _uses_legacy_source_revision_schema(conn: Connection) -> bool:
    columns = _source_revision_columns(conn)
    return {"worker", "entity_type", "entity_id", "source_hash"}.issubset(columns)


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
    """Create source_revision table if it doesn't exist (idempotent).
    
    Adds dgt_url column for persistent discovery queue if missing.
    """
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
                dgt_url TEXT,
                UNIQUE(worker_name, source_entity_tipo, source_entity_id)
            )
        """
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
                dgt_url TEXT,
                UNIQUE(worker_name, source_entity_tipo, source_entity_id)
            )
        """

    conn.execute(text(ddl))

    # Add dgt_url column if missing (migration for existing deployments)
    columns = _source_revision_columns(conn)
    if "dgt_url" not in columns:
        if dialect_name == "sqlite":
            conn.execute(text("ALTER TABLE source_revision ADD COLUMN dgt_url TEXT"))
        else:
            conn.execute(text(
                "ALTER TABLE source_revision ADD COLUMN dgt_url TEXT"
            ))

    if _uses_legacy_source_revision_schema(conn):
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_source_revision_worker_entity
                ON source_revision(worker, entity_type, entity_id)
        """))
    else:
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_source_revision_worker_entity
                ON source_revision(worker_name, source_entity_tipo, source_entity_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_source_revision_pending_dgt
                ON source_revision(worker_name, source_entity_tipo, content_hash_sha256)
                WHERE content_hash_sha256 = 'pending' AND dgt_url IS NOT NULL
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

    if _uses_legacy_source_revision_schema(conn):
        row = conn.execute(
            text("""
                SELECT source_hash, NULL, NULL
                FROM source_revision
                WHERE worker = :worker
                  AND entity_type = :tipo
                  AND entity_id = :entity_id
            """),
            {"worker": worker_name, "tipo": source_entity_tipo, "entity_id": source_entity_id},
        ).fetchone()
    else:
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

    if new_hash == old_hash:
        return SourceChange(changed=False, old_hash=old_hash)

    return SourceChange(
        changed=True,
        old_hash=old_hash,
        new_hash=new_hash,
        etag=etag,
        last_modified=last_modified,
    )


def destination_row_exists(
    conn: Connection,
    table_name: str,
    id_column: str,
    id_value: str,
) -> bool:
    """Return True when the target row exists in the destination table."""
    return bool(
        conn.execute(
            text(
                f"""
                SELECT 1
                FROM {table_name}
                WHERE {id_column} = :id_value
                LIMIT 1
                """
            ),
            {"id_value": id_value},
        ).scalar()
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
    """Record a revision after processing content. Upserts atomically.

    Uses a per-entity advisory lock to prevent deadlocks when multiple
    connections in the same process try to upsert the same source_revision
    row concurrently. Retries once on deadlock detection.
    """
    new_hash = compute_content_hash(content)
    content_length = len(content.encode("utf-8")) if isinstance(content, str) else len(content)
    dialect_name = conn.engine.dialect.name
    ts_func = "datetime('now')" if dialect_name == "sqlite" else "now()"

    if dialect_name == "postgresql":
        # Per-entity advisory lock — only serializes writes to the same
        # entity_id, allowing parallel writes across different entities.
        lock_key = f"{worker_name}:{source_entity_tipo}:{source_entity_id}"
        conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": lock_key},
        )

    if _uses_legacy_source_revision_schema(conn):
        conn.execute(text(f"""
            INSERT INTO source_revision (
                worker, entity_type, entity_id, source_hash,
                source_url, first_seen_at, last_seen_at
            ) VALUES (:worker, :tipo, :entity_id, :hash, NULL, {ts_func}, {ts_func})
            ON CONFLICT (worker, entity_type, entity_id)
            DO UPDATE SET
                source_hash = EXCLUDED.source_hash,
                last_seen_at = {ts_func}
        """), {
            "worker": worker_name,
            "tipo": source_entity_tipo,
            "entity_id": source_entity_id,
            "hash": new_hash,
        })
        return

    conn.execute(text(f"""
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
            fetched_at = {ts_func}
    """), {
        "worker": worker_name,
        "tipo": source_entity_tipo,
        "entity_id": source_entity_id,
        "hash": new_hash,
        "etag": etag,
        "lm": last_modified,
        "length": content_length,
    })


def invalidate_old_embeddings(
    conn: Connection,
    source_entity_id: str,
) -> int:
    """Invalidate (NULL) old embeddings for entities whose content changed.

    Convenience wrapper around invalidate_old_embeddings_by_entity()
    for the version_articulo table (BOE worker).

    Returns count of invalidated rows.
    """
    return invalidate_old_embeddings_by_entity(
        conn,
        entity_table="version_articulo",
        entity_id_column="boe_bloque_id",
        entity_id_value=source_entity_id,
    )


def invalidate_old_embeddings_by_entity(
    conn: Connection,
    entity_table: str,
    entity_id_column: str,
    entity_id_value: str,
) -> int:
    """Invalidate (NULL) old embeddings for a specific entity.

    Sets embedding = NULL, embedding_model_name = NULL, content_hash = NULL
    for all rows matching the entity identifier.

    Returns count of invalidated rows.
    """
    dialect_name = conn.engine.dialect.name
    if dialect_name == "sqlite":
        cols = conn.execute(text(f"PRAGMA table_info({entity_table})")).fetchall()
        has_embedding = any(row[1] == "embedding" for row in cols)
    else:
        has_embedding = bool(
            conn.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = :table_name
                      AND column_name = 'embedding'
                    LIMIT 1
                    """
                ),
                {"table_name": entity_table},
            ).scalar()
        )

    if not has_embedding:
        return 0

    # Count rows that will be invalidated before updating.
    count = conn.execute(
        text(f"""
            SELECT COUNT(*) FROM {entity_table}
            WHERE {entity_id_column} = :entity_id
              AND embedding IS NOT NULL
        """),
        {"entity_id": entity_id_value},
    ).scalar()

    if count > 0:
        conn.execute(
            text(f"""
                UPDATE {entity_table}
                SET embedding = NULL,
                    embedding_model_name = NULL,
                    content_hash = NULL
                WHERE {entity_id_column} = :entity_id
                  AND embedding IS NOT NULL
            """),
            {"entity_id": entity_id_value},
        )

    return count


def record_embedding_version(
    conn: Connection,
    entity_table: str,
    entity_id: int,
    model_name: str,
    content_hash: str,
    dimensions: int,
) -> None:
    """Record an embedding version in embedding_version for audit trail.

    Inserts a new row marking this as the current active version.
    If a previous active version exists for this entity+model,
    marks it as invalidated_at.
    """
    conn.execute(
        text("""
            INSERT INTO embedding_version (entity_table, entity_id, model_name, content_hash, dimensions, invalidated_at)
            VALUES (:entity_table, :entity_id, :model_name, :content_hash, :dimensions, NULL)
            ON CONFLICT (entity_table, entity_id, model_name, content_hash) DO NOTHING
        """),
        {
            "entity_table": entity_table,
            "entity_id": entity_id,
            "model_name": model_name,
            "content_hash": content_hash,
            "dimensions": dimensions,
        },
    )

    # Mark old active versions for this entity+model as invalidated
    dialect_name = conn.engine.dialect.name
    ts_func = "CURRENT_TIMESTAMP" if dialect_name != "sqlite" else "datetime('now')"
    conn.execute(
        text(f"""
            UPDATE embedding_version
            SET invalidated_at = {ts_func}
            WHERE entity_table = :entity_table
              AND entity_id = :entity_id
              AND model_name = :model_name
              AND invalidated_at IS NULL
              AND content_hash != :content_hash
        """),
        {
            "entity_table": entity_table,
            "entity_id": entity_id,
            "model_name": model_name,
            "content_hash": content_hash,
        },
    )
