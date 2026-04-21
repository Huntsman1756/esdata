"""modelo campana operativa

Revision ID: 20260418_0002
Revises: 20260416_0001
Create Date: 2026-04-18 18:30:00
"""

from alembic import op


revision = "20260418_0002"
down_revision = "20260416_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS modelo_campana_operativa (
            campana_id INTEGER PRIMARY KEY REFERENCES modelo_campana(id) ON DELETE CASCADE,
            categoria_obligado TEXT,
            frecuencia_presentacion TEXT,
            ventana_presentacion TEXT,
            canal_presentacion TEXT,
            obligados_resumen TEXT,
            plazo_resumen TEXT,
            presentacion_resumen TEXT,
            norma_base TEXT,
            nota TEXT,
            actualizado_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS modelo_campana_operativa")
