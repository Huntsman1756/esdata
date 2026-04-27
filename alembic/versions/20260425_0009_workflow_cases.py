"""add workflow_cases table for compliance workflow tracking

Creates the workflow_cases table to support compliance workflow operations:
tracking regulatory changes from detection through resolution with
structured fields for ownership, evidence, checklists, and outcomes.

Revision ID: 20260425_0009_workflow_cases
Revises: 20260425_0008_obligaciones_operativas
Create Date: 2026-04-25 00:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "20260425_0009_workflow_cases"
down_revision = "20260425_0008_obligaciones_operativas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_cases",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_id", sa.Text(), nullable=False, unique=True),
        sa.Column("cambio_codigo", sa.Text(), nullable=False),
        sa.Column("obligacion_codigo", sa.Text(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False, server_default=sa.text("'pendiente_revision'::text")),
        sa.Column("owner_rol", sa.Text(), nullable=False),
        sa.Column("fecha_objetivo", sa.Date(), nullable=False),
        sa.Column("evidencia_requerida", sa.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("checklist", sa.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("resultado_revision", sa.Text(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("accion_recomendada_confirmada", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_cases_estado
            ON workflow_cases(estado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_cases_obligacion
            ON workflow_cases(obligacion_codigo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_cases_owner
            ON workflow_cases(owner_rol)
        """
    )

    # Seed initial case
    op.execute(
        """
        INSERT INTO workflow_cases (
            workflow_id, cambio_codigo, obligacion_codigo, estado, owner_rol,
            fecha_objetivo, evidencia_requerida, checklist
        )
        SELECT
            'WF-001',
            'CAMBIO-CNMV-001',
            'CNMV-IR-RESERVADA',
            'pendiente_revision',
            'compliance',
            '2026-05-05'::date,
            ARRAY['analisis_impacto', 'actualizacion_calendario'],
            ARRAY['validar impacto normativo', 'asignar responsable', 'confirmar fecha objetivo']
        WHERE NOT EXISTS (
            SELECT 1 FROM workflow_cases WHERE workflow_id = 'WF-001'
        )
        """
    )


def downgrade() -> None:
    op.drop_table("workflow_cases")
