"""add EU metadata columns to norma

Revision ID: 20260517_0080_norma_eu_metadata
Revises: 20260517_0079_profile_applicability_tables
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260517_0080_norma_eu_metadata"
down_revision = "20260517_0079_profile_applicability_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS celex VARCHAR(20)")
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS tipo_norma VARCHAR(30)")
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS publicacion_doue DATE")
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS url_eurlex TEXT")
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS vigente BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE norma ADD COLUMN IF NOT EXISTS derogada_por VARCHAR(50)")
    op.create_index(
        "ix_norma_celex",
        "norma",
        ["celex"],
        unique=False,
        postgresql_where=sa.text("celex IS NOT NULL"),
    )
    op.create_index(
        "ix_norma_tipo_norma",
        "norma",
        ["tipo_norma"],
        unique=False,
        postgresql_where=sa.text("tipo_norma IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_norma_tipo_norma", table_name="norma", if_exists=True)
    op.drop_index("ix_norma_celex", table_name="norma", if_exists=True)
    op.drop_column("norma", "derogada_por", if_exists=True)
    op.drop_column("norma", "vigente", if_exists=True)
    op.drop_column("norma", "url_eurlex", if_exists=True)
    op.drop_column("norma", "publicacion_doue", if_exists=True)
    op.drop_column("norma", "tipo_norma", if_exists=True)
    op.drop_column("norma", "celex", if_exists=True)
