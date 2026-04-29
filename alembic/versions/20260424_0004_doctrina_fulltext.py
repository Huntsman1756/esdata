"""add search_vector to documento_interpretativo

# Revision ID: 20260424_0004_doctrina_fulltext
# Revises: 20260418_0003
# Create Date: 2026-04-24 00:00:00
"""

from alembic import op


revision = "20260424_0004_doctrina_fulltext"
down_revision = "20260418_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE documento_interpretativo
        ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
        """
    )
    op.execute(
        """
        UPDATE documento_interpretativo
        SET search_vector = to_tsvector('spanish', COALESCE(titulo, '') || ' ' || texto)
        WHERE search_vector IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_interpretativo_search_vector
        ON documento_interpretativo USING GIN (search_vector)
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_documento_interpretativo_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.titulo, '') || ' ' || NEW.texto);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_documento_interpretativo_search_vector
        ON documento_interpretativo
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_documento_interpretativo_search_vector
        BEFORE INSERT OR UPDATE ON documento_interpretativo
        FOR EACH ROW EXECUTE FUNCTION update_documento_interpretativo_search_vector()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_documento_interpretativo_search_vector
        ON documento_interpretativo
        """
    )
    op.execute(
        """
        DROP FUNCTION IF EXISTS update_documento_interpretativo_search_vector()
        """
    )
    op.execute(
        """
        DROP INDEX IF EXISTS idx_documento_interpretativo_search_vector
        """
    )
    op.execute(
        """
        ALTER TABLE documento_interpretativo
        DROP COLUMN IF EXISTS search_vector
        """
    )
