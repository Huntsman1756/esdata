"""add operational fields to obligacion_regulatoria

Add structured operational data to obligations: deadlines, penalties,
triggers, submission channels, and statute of limitations.

This enables MCP consumers (LLMs) to answer compliance questions with
concrete data instead of requiring the LLM to parse free-text documents.

Revision ID: 20260425_0008_obligaciones_operativas
Revises: 20260425_0007_critical_indexes
Create Date: 2026-04-25 00:00:00

"""

from alembic import op

revision = "20260425_0008_obligaciones_operativas"
down_revision = "20260425_0007_critical_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE obligacion_regulatoria
        ADD COLUMN IF NOT EXISTS plazo_dias INTEGER,
        ADD COLUMN IF NOT EXISTS frecuencia_presentacion TEXT,
        ADD COLUMN IF NOT EXISTS ventana_presentacion TEXT,
        ADD COLUMN IF NOT EXISTS trigger_presentacion TEXT,
        ADD COLUMN IF NOT EXISTS canal_presentacion TEXT,
        ADD COLUMN IF NOT EXISTS obligados_resumen TEXT,
        ADD COLUMN IF NOT EXISTS sancion_min NUMERIC(10,2),
        ADD COLUMN IF NOT EXISTS sancion_max NUMERIC(10,2),
        ADD COLUMN IF NOT EXISTS recargo_voluntario TEXT,
        ADD COLUMN IF NOT EXISTS recargo_involuntario TEXT,
        ADD COLUMN IF NOT EXISTS interes_demora TEXT,
        ADD COLUMN IF NOT EXISTS prescripcion_anos INTEGER,
        ADD COLUMN IF NOT EXISTS deposito_previo TEXT,
        ADD COLUMN IF NOT EXISTS fuentes_operativas JSONB,
        ADD COLUMN IF NOT EXISTS ultima_actualizacion TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS origen_metadato TEXT DEFAULT 'seed_curado',
        ADD COLUMN IF NOT EXISTS estado_metadato TEXT DEFAULT 'curado'
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_obligacion_frecuencia
            ON obligacion_regulatoria(frecuencia_presentacion)
            WHERE frecuencia_presentacion IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_obligacion_ambito
            ON obligacion_regulatoria(ambito)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_obligacion_estado
            ON obligacion_regulatoria(estado_vigencia)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE obligacion_regulatoria
        DROP COLUMN IF EXISTS plazo_dias,
        DROP COLUMN IF EXISTS frecuencia_presentacion,
        DROP COLUMN IF EXISTS ventana_presentacion,
        DROP COLUMN IF EXISTS trigger_presentacion,
        DROP COLUMN IF EXISTS canal_presentacion,
        DROP COLUMN IF EXISTS obligados_resumen,
        DROP COLUMN IF EXISTS sancion_min,
        DROP COLUMN IF EXISTS sancion_max,
        DROP COLUMN IF EXISTS recargo_voluntario,
        DROP COLUMN IF EXISTS recargo_involuntario,
        DROP COLUMN IF EXISTS interes_demora,
        DROP COLUMN IF EXISTS prescripcion_anos,
        DROP COLUMN IF EXISTS deposito_previo,
        DROP COLUMN IF EXISTS fuentes_operativas,
        DROP COLUMN IF EXISTS ultima_actualizacion,
        DROP COLUMN IF EXISTS origen_metadato,
        DROP COLUMN IF EXISTS estado_metadato
        """
    )

    op.execute("DROP INDEX IF EXISTS idx_obligacion_frecuencia")
    op.execute("DROP INDEX IF EXISTS idx_obligacion_ambito")
    op.execute("DROP INDEX IF EXISTS idx_obligacion_estado")
