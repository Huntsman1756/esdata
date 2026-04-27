"""add ambitos column to linea_criterio

Revision ID: 20260426_0020_linea_criterio_ambitos
Revises: 20260426_0019_linea_criterio
Create Date: 2026-04-26

Adds an `ambitos` TEXT[] column to linea_criterio to track which
documentary domains (jurisprudencia_tributaria,
jurisprudencia_pbcft, jurisprudencia_mercantil_regulatoria) are
covered by each curated line.

Seeds `ambitos` on existing seed rows based on their
cuestion_practica content.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260426_0020_linea_criterio_ambitos"
down_revision: str | None = "20260426_0019_linea_criterio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE linea_criterio
        ADD COLUMN IF NOT EXISTS ambitos VARCHAR[] DEFAULT '{}'
        """
    )

    # Seed ambitos on existing seed rows based on cuestion_practica
    op.execute(
        """
        UPDATE linea_criterio
        SET ambitos = ARRAY['jurisprudencia_tributaria']
        WHERE titulo ILIKE '%iva%'
        """
    )
    op.execute(
        """
        UPDATE linea_criterio
        SET ambitos = ARRAY['jurisprudencia_pbcft']
        WHERE titulo ILIKE '%lavado%' OR titulo ILIKE '%blanqueo%'
        """
    )
    op.execute(
        """
        UPDATE linea_criterio
        SET ambitos = ARRAY['jurisprudencia_mercantil_regulatoria']
        WHERE titulo ILIKE '%comision%'
           OR titulo ILIKE '%ejecucion%'
           OR titulo ILIKE '%adecuacion%'
           OR titulo ILIKE '%gobierno de productos%'
        """
    )
    op.execute(
        """
        UPDATE linea_criterio
        SET ambitos = ARRAY['jurisprudencia_tributaria', 'jurisprudencia_mercantil_regulatoria']
        WHERE titulo ILIKE '%informacion privilegiada%'
           OR titulo ILIKE '%insider%'
        """
    )


def downgrade() -> None:
    op.drop_column("linea_criterio", "ambitos")
