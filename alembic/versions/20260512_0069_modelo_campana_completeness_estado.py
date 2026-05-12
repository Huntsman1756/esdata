"""modelo campaign explicit completeness status

Revision ID: 20260512_0069_modelo_campana_completeness_estado
Revises: 20260511_0068_freshness_tables_schema
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op


revision = "20260512_0069_modelo_campana_completeness_estado"
down_revision = "20260511_0068_freshness_tables_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        ADD COLUMN IF NOT EXISTS completeness_estado TEXT
        """
    )
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        DROP CONSTRAINT IF EXISTS ck_modelo_campana_operativa_completeness_estado
        """
    )
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        ADD CONSTRAINT ck_modelo_campana_operativa_completeness_estado
        CHECK (
            completeness_estado IS NULL
            OR completeness_estado IN (
                'completa',
                'parcial',
                'no-casillas-expected',
                'deprecated'
            )
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        DROP CONSTRAINT IF EXISTS ck_modelo_campana_operativa_completeness_estado
        """
    )
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        DROP COLUMN IF EXISTS completeness_estado
        """
    )
