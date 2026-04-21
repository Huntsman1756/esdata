"""modelo campana operativa provenance

Revision ID: 20260418_0003
Revises: 20260418_0002
Create Date: 2026-04-18 19:20:00
"""

from alembic import op


revision = "20260418_0003"
down_revision = "20260418_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        ADD COLUMN IF NOT EXISTS origen_metadato TEXT DEFAULT 'seed_curado'
        """
    )
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        ADD COLUMN IF NOT EXISTS estado_metadato TEXT DEFAULT 'curado'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        DROP COLUMN IF EXISTS origen_metadato
        """
    )
    op.execute(
        """
        ALTER TABLE modelo_campana_operativa
        DROP COLUMN IF EXISTS estado_metadato
        """
    )
