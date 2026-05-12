"""add document metadata for BOE diario ingestion

Revision ID: 20260512_0072_documento_interpretativo_metadata
Revises: 20260512_0071_eurlex_empty_official_blocks
Create Date: 2026-05-12
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260512_0072_documento_interpretativo_metadata"
down_revision = "20260512_0071_eurlex_empty_official_blocks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS metadata JSONB"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS row_completeness TEXT DEFAULT 'partial'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS row_provenance TEXT DEFAULT 'official_best_effort'"
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE documento_interpretativo
            SET metadata = COALESCE(metadata, '{}'::jsonb),
                row_completeness = COALESCE(row_completeness, 'partial'),
                row_provenance = COALESCE(row_provenance, 'official_best_effort')
            WHERE metadata IS NULL
               OR row_completeness IS NULL
               OR row_provenance IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ALTER COLUMN metadata SET DEFAULT '{}'::jsonb"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("ALTER TABLE documento_interpretativo ALTER COLUMN metadata DROP DEFAULT")
    )
    op.execute(
        sa.text("ALTER TABLE documento_interpretativo DROP COLUMN IF EXISTS metadata")
    )
