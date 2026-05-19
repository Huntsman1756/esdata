"""add sujeto_obligado to documento_interpretativo

Revision ID: 20260519_0082_documento_interpretativo_sujeto_obligado
Revises: 20260518_0081_norma_parent_celex
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op


revision = "20260519_0082_documento_interpretativo_sujeto_obligado"
down_revision = "20260518_0081_norma_parent_celex"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS sujeto_obligado TEXT[]")


def downgrade() -> None:
    op.drop_column("documento_interpretativo", "sujeto_obligado", if_exists=True)
