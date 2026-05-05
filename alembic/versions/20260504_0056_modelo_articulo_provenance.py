"""add exact key and provenance to modelo_articulo

# Revision ID: 20260504_0056_modelo_articulo_provenance
# Revises: 20260503_0055_query_audit_response_payload
# Create Date: 2026-05-04 00:56:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260504_0056_modelo_articulo_provenance"
down_revision = "20260503_0055_query_audit_response_payload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE modelo_articulo ADD COLUMN IF NOT EXISTS norma TEXT"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ADD COLUMN IF NOT EXISTS numero TEXT"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ADD COLUMN IF NOT EXISTS metodo_enlace TEXT"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ADD COLUMN IF NOT EXISTS confianza_enlace NUMERIC(3,2)"))

    op.execute(
        sa.text(
            """
            UPDATE modelo_articulo ma
            SET norma = n.codigo,
                numero = a.numero,
                metodo_enlace = COALESCE(ma.metodo_enlace, 'legacy_numero_only'),
                confianza_enlace = COALESCE(ma.confianza_enlace, 0.0)
            FROM articulo a
            JOIN norma n ON n.id = a.norma_id
            WHERE a.id = ma.articulo_id
            """
        )
    )

    op.execute(sa.text("ALTER TABLE modelo_articulo ALTER COLUMN norma SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ALTER COLUMN numero SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ALTER COLUMN metodo_enlace SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ALTER COLUMN confianza_enlace SET NOT NULL"))

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE modelo_articulo
                ADD CONSTRAINT ck_modelo_articulo_confianza_enlace_range
                CHECK (confianza_enlace >= 0.0 AND confianza_enlace <= 1.0);
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )

    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_modelo_articulo_modelo_norma_numero ON modelo_articulo (modelo_id, norma, numero)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ux_modelo_articulo_modelo_norma_numero"))
    op.execute(
        sa.text(
            "ALTER TABLE modelo_articulo DROP CONSTRAINT IF EXISTS ck_modelo_articulo_confianza_enlace_range"
        )
    )
    op.execute(sa.text("ALTER TABLE modelo_articulo DROP COLUMN IF EXISTS confianza_enlace"))
    op.execute(sa.text("ALTER TABLE modelo_articulo DROP COLUMN IF EXISTS metodo_enlace"))
    op.execute(sa.text("ALTER TABLE modelo_articulo DROP COLUMN IF EXISTS numero"))
    op.execute(sa.text("ALTER TABLE modelo_articulo DROP COLUMN IF EXISTS norma"))
