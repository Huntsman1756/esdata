"""fix LIVA article 163 sexvicies identifier typo

Revision ID: 20260513_0076_liva_163_sexvicies_typo
Revises: 20260513_0075_casp_source_traceability
Create Date: 2026-05-13

The official BOE consolidated text uses "Articulo 163 sexvicies". A previous
ingestion left the article identifier as "163 sexvivies", which breaks exact
article retrieval for the official identifier.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260513_0076_liva_163_sexvicies_typo"
down_revision = "20260513_0075_casp_source_traceability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE articulo
            SET numero = '163 sexvicies',
                titulo = REPLACE(titulo, 'sexvivies', 'sexvicies')
            WHERE numero = '163 sexvivies'
              AND norma_id = (
                  SELECT id
                  FROM norma
                  WHERE codigo = 'LIVA'
                     OR boe_id = 'BOE-A-1992-28740'
                  LIMIT 1
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE articulo
            SET numero = '163 sexvivies',
                titulo = REPLACE(titulo, 'sexvicies', 'sexvivies')
            WHERE numero = '163 sexvicies'
              AND norma_id = (
                  SELECT id
                  FROM norma
                  WHERE codigo = 'LIVA'
                     OR boe_id = 'BOE-A-1992-28740'
                  LIMIT 1
              )
            """
        )
    )
