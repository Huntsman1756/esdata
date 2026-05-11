"""add source_revision table for incremental change detection

# Revision ID: 20260427_0033_source_revision_tracking
# Revises: 987eafbc4c83
# Create Date: 2026-04-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260427_0033_source_revision_tracking"
down_revision = "987eafbc4c83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS source_revision (
            id SERIAL PRIMARY KEY,
            worker_name TEXT NOT NULL,
            source_entity_tipo TEXT NOT NULL,
            source_entity_id TEXT NOT NULL,
            content_hash_sha256 TEXT NOT NULL,
            etag TEXT,
            last_modified TEXT,
            content_length INTEGER,
            fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            UNIQUE (worker_name, source_entity_tipo, source_entity_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_source_revision_worker_entity
        ON source_revision (worker_name, source_entity_tipo, source_entity_id)
        """
    )


def downgrade() -> None:
    op.drop_index("idx_source_revision_worker_entity", table_name="source_revision")
    op.drop_table("source_revision")
