"""add embedding versioning columns

- embedding_model_name TEXT on version_articulo, documento_fragmento, documento_interpretativo
- content_hash TEXT on the same tables (hash of the text that was embedded)
- embedding_version table for tracking embedding history per entity

# Revision ID: 20260427_0034_embedding_versioning
# Revises: 20260427_0033_source_revision_tracking
# Create Date: 2026-04-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260427_0034_embedding_versioning"
down_revision = "20260427_0033_source_revision_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add embedding_model_name and content_hash to tables with embeddings
    op.execute("""ALTER TABLE version_articulo ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE version_articulo ADD COLUMN IF NOT EXISTS content_hash TEXT""")
    op.execute("""ALTER TABLE documento_fragmento ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE documento_fragmento ADD COLUMN IF NOT EXISTS content_hash TEXT""")
    op.execute("""ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS content_hash TEXT""")

    # Create embedding_version tracking table
    op.create_table(
        "embedding_version",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_table", sa.Text(), nullable=False, comment="version_articulo, documento_fragmento, documento_interpretativo"),
        sa.Column("entity_id", sa.Integer(), nullable=False, comment="PK of the entity row"),
        sa.Column("model_name", sa.Text(), nullable=False, comment="embedding model name"),
        sa.Column("content_hash", sa.Text(), nullable=False, comment="hash of the embedded text"),
        sa.Column("dimensions", sa.Integer(), nullable=False, comment="embedding dimension"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True, comment="NULL means currently active"),
        sa.UniqueConstraint("entity_table", "entity_id", "model_name", "content_hash", name="uq_embedding_version"),
    )

    op.create_index(
        "idx_embedding_version_entity",
        "embedding_version",
        ["entity_table", "entity_id"],
    )

    op.create_index(
        "idx_embedding_version_model",
        "embedding_version",
        ["model_name"],
    )


def downgrade() -> None:
    op.drop_index("idx_embedding_version_model")
    op.drop_index("idx_embedding_version_entity")
    op.drop_table("embedding_version")

    op.drop_column("documento_interpretativo", "content_hash")
    op.drop_column("documento_interpretativo", "embedding_model_name")
    op.drop_column("documento_fragmento", "content_hash")
    op.drop_column("documento_fragmento", "embedding_model_name")
    op.drop_column("version_articulo", "content_hash")
    op.drop_column("version_articulo", "embedding_model_name")
