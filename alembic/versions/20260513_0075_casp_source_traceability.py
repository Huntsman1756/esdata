"""add CASP source traceability fields

Revision ID: 20260513_0075_casp_source_traceability
Revises: 20260513_0074_eurlex_esma_market_tables
Create Date: 2026-05-13

CASP rows are loaded from ESMA's official Interim MiCA Register CSV.
This migration adds row-level provenance and verification fields so the API
can distinguish official CASP rows from unavailable non-CASP MiCA domains.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260513_0075_casp_source_traceability"
down_revision = "20260513_0074_eurlex_esma_market_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE casp ADD COLUMN IF NOT EXISTS source_url TEXT"))
    op.execute(sa.text("ALTER TABLE casp ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64)"))
    op.execute(sa.text("ALTER TABLE casp ADD COLUMN IF NOT EXISTS capture_date DATE"))
    op.execute(sa.text("ALTER TABLE casp ADD COLUMN IF NOT EXISTS verified BOOLEAN NOT NULL DEFAULT false"))
    op.execute(sa.text("ALTER TABLE casp ADD COLUMN IF NOT EXISTS completeness VARCHAR(50) NOT NULL DEFAULT 'parcial'"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_casp_verified ON casp(verified)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_casp_capture_date ON casp(capture_date)"))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_casp_capture_date"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_casp_verified"))
    op.execute(sa.text("ALTER TABLE casp DROP COLUMN IF EXISTS completeness"))
    op.execute(sa.text("ALTER TABLE casp DROP COLUMN IF EXISTS verified"))
    op.execute(sa.text("ALTER TABLE casp DROP COLUMN IF EXISTS capture_date"))
    op.execute(sa.text("ALTER TABLE casp DROP COLUMN IF EXISTS source_hash"))
    op.execute(sa.text("ALTER TABLE casp DROP COLUMN IF EXISTS source_url"))
