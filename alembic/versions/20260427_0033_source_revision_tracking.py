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
    op.create_table(
        "source_revision",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("worker_name", sa.Text(), nullable=False),
        sa.Column("source_entity_tipo", sa.Text(), nullable=False),
        sa.Column("source_entity_id", sa.Text(), nullable=False),
        sa.Column("content_hash_sha256", sa.Text(), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified", sa.Text(), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "worker_name", "source_entity_tipo", "source_entity_id"
        ),
    )
    op.create_index(
        "idx_source_revision_worker_entity",
        "source_revision",
        ["worker_name", "source_entity_tipo", "source_entity_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_source_revision_worker_entity", table_name="source_revision")
    op.drop_table("source_revision")
