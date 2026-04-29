"""add pgc tables for Plan General Contable

Creates the pgc_marco, pgc_norma_valoracion, pgc_cuenta,
pgc_estado_financiero, pgc_cuenta_fiscal_ref, and pgc_cuenta_modelo_aeat_ref
tables to support the Spanish Plan General Contable (PGC) data model.

# Revision ID: 20260425_0010_pgc
# Revises: 20260425_0009_workflow_cases
# Create Date: 2026-04-25 00:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "20260425_0010_pgc"
down_revision = "20260425_0009_workflow_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgc_marco: conceptual framework / validation standards
    op.create_table(
        "pgc_marco",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo", sa.Text(), nullable=False, unique=True),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=True),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("url_boe", sa.Text(), nullable=True),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_marco_tipo
            ON pgc_marco(tipo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_marco_vigente
            ON pgc_marco(vigente)
        """
    )

    # pgc_norma_valoracion: valuation rules linked to marco and accounts
    op.create_table(
        "pgc_norma_valoracion",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("marco_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("cuenta_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("norma_ref", sa.Text(), nullable=False),
        sa.Column("articulo", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tipo_operacion", sa.Text(), nullable=True),
        sa.Column("debe_haber", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_norma_valoracion_marco
            ON pgc_norma_valoracion(marco_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_norma_valoracion_cuenta
            ON pgc_norma_valoracion(cuenta_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_norma_valoracion_norma
            ON pgc_norma_valoracion(norma_ref)
        """
    )

    # pgc_cuenta: chart of accounts
    op.create_table(
        "pgc_cuenta",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo", sa.Text(), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("nivel", sa.Integer(), nullable=False),
        sa.Column("padre_codigo", sa.Text(), nullable=True),
        sa.Column("grupo", sa.Text(), nullable=True),
        sa.Column("clase", sa.Text(), nullable=True),
        sa.Column("saldo_normal", sa.Text(), nullable=True),
        sa.Column("tipo_cuenta", sa.Text(), nullable=True),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_nivel
            ON pgc_cuenta(nivel)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_grupo
            ON pgc_cuenta(grupo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_clase
            ON pgc_cuenta(clase)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_padre
            ON pgc_cuenta(padre_codigo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_vigente
            ON pgc_cuenta(vigente)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_codigo_trgm
            ON pgc_cuenta USING gin (codigo gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_desc_trgm
            ON pgc_cuenta USING gin (descripcion gin_trgm_ops)
        """
    )

    # pgc_estado_financiero: financial statement line items
    op.create_table(
        "pgc_estado_financiero",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cuenta_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("tipo_presentacion", sa.Text(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.Text(), nullable=False),
        sa.Column("importe_base", sa.Numeric(18, 2), nullable=True),
        sa.Column("importe_anterior", sa.Numeric(18, 2), nullable=True),
        sa.Column("nota_pieds", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_estado_financiero_cuenta
            ON pgc_estado_financiero(cuenta_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_estado_financiero_estado
            ON pgc_estado_financiero(estado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_estado_financiero_periodo
            ON pgc_estado_financiero(periodo)
        """
    )

    # pgc_cuenta_fiscal_ref: PGC account <-> tax model linkage
    op.create_table(
        "pgc_cuenta_fiscal_ref",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cuenta_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("modelo", sa.Text(), nullable=False),
        sa.Column("casilla", sa.Text(), nullable=True),
        sa.Column("ejercicio", sa.Text(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_fiscal_ref_cuenta
            ON pgc_cuenta_fiscal_ref(cuenta_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_fiscal_ref_modelo
            ON pgc_cuenta_fiscal_ref(modelo)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uix_pgc_cuenta_fiscal_ref
            ON pgc_cuenta_fiscal_ref(cuenta_id, modelo, casilla, ejercicio)
        """
    )

    # pgc_cuenta_modelo_aeat_ref: PGC account <-> AEAT model linkage
    op.create_table(
        "pgc_cuenta_modelo_aeat_ref",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cuenta_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("modelo_id", sa.Integer(), nullable=False),
        sa.Column("campana", sa.Text(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_modelo_aeat_ref_cuenta
            ON pgc_cuenta_modelo_aeat_ref(cuenta_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_modelo_aeat_ref_modelo
            ON pgc_cuenta_modelo_aeat_ref(modelo_id)
        """
    )

    # Las tablas futuras se crean ya para evitar churn de esquema, pero sus datos y
    # endpoints funcionales quedan diferidos a las subfases 11.2-11.5. El seed de
    # marco y cuentas tambien se difiere al worker para que sea la unica fuente de
    # datos iniciales del slice 11.1.


def downgrade() -> None:
    op.drop_table("pgc_cuenta_modelo_aeat_ref")
    op.drop_table("pgc_cuenta_fiscal_ref")
    op.drop_table("pgc_estado_financiero")
    op.drop_table("pgc_cuenta")
    op.drop_table("pgc_norma_valoracion")
    op.drop_table("pgc_marco")
