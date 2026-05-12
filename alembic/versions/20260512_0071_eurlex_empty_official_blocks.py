"""eurlex empty official block counter

Revision ID: 20260512_0071_eurlex_empty_official_blocks
Revises: 20260512_0070_eurlex_quality_counters
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op

revision = "20260512_0071_eurlex_empty_official_blocks"
down_revision = "20260512_0070_eurlex_quality_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS articles_empty_official INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE norma DROP COLUMN IF EXISTS articles_empty_official")
