"""add parent CELEX metadata to norma

Revision ID: 20260518_0081_norma_parent_celex
Revises: 20260517_0080_norma_eu_metadata
Create Date: 2026-05-18
"""

from __future__ import annotations

from alembic import op


revision = "20260518_0081_norma_parent_celex"
down_revision = "20260517_0080_norma_eu_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS norma_padre_celex TEXT")


def downgrade() -> None:
    op.drop_column("norma", "norma_padre_celex", if_exists=True)
