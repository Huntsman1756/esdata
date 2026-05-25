"""remove legacy non-XSD fields from AEAT 290 current campaign

Revision ID: 20260525_0101_aeat_290_remove_legacy_fields
Revises: 20260525_0100_aeat_290_current_docs_2025
Create Date: 2026-05-25

The current Modelo 290 documentation is the official GI38 XSD/WSDL contract.
Any legacy non-XSD fallback fields copied into campaign 2025 must stay inactive
so the API/MCP exposes the 152 official XSD fields only.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0101_aeat_290_remove_legacy_fields"
down_revision = "20260525_0100_aeat_290_current_docs_2025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE modelo_casilla cs
            SET activa = false
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE cs.campana_id = mc.id
              AND am.codigo = '290'
              AND mc.campana = '2025'
              AND cs.activa = true
              AND cs.tipo_casilla <> 'diseno_registro_xsd_campo'
            """
        )
    )


def downgrade() -> None:
    # Intentionally irreversible: reactivating legacy fallback fields would
    # reintroduce stale non-XSD data into the current Modelo 290 contract.
    pass
