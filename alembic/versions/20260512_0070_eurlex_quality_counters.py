"""eurlex quality counters on norma

Revision ID: 20260512_0070_eurlex_quality_counters
Revises: 20260512_0069_modelo_campana_completeness_estado
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op

revision = "20260512_0070_eurlex_quality_counters"
down_revision = "20260512_0069_modelo_campana_completeness_estado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS articles_expected INTEGER")
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS articles_parsed INTEGER")
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS quality_status TEXT")
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS quality_checked_at TIMESTAMPTZ")
    op.execute(
        """
        ALTER TABLE norma
        DROP CONSTRAINT IF EXISTS ck_norma_quality_status
        """
    )
    op.execute(
        """
        ALTER TABLE norma
        ADD CONSTRAINT ck_norma_quality_status
        CHECK (
            quality_status IS NULL
            OR quality_status IN (
                'metadata_only',
                'partial',
                'article_text_available'
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE norma DROP CONSTRAINT IF EXISTS ck_norma_quality_status")
    op.execute("ALTER TABLE norma DROP COLUMN IF EXISTS quality_checked_at")
    op.execute("ALTER TABLE norma DROP COLUMN IF EXISTS quality_status")
    op.execute("ALTER TABLE norma DROP COLUMN IF EXISTS articles_parsed")
    op.execute("ALTER TABLE norma DROP COLUMN IF EXISTS articles_expected")
