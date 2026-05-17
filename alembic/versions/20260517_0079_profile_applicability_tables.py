"""add profile applicability tables

Revision ID: 20260517_0079_profile_applicability_tables
Revises: 20260514_0078_cnmv_consolidated_version_audit
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260517_0079_profile_applicability_tables"
down_revision = "20260514_0078_cnmv_consolidated_version_audit"
branch_labels = None
depends_on = None


RLS_TABLES = (
    "perfil_entidad",
    "obligacion_perfil",
    "obligacion_fuente",
)


def _enable_rls(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE IF EXISTS {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = '{table_name}'
                      AND policyname = 'esdata_all'
                ) THEN
                    EXECUTE 'CREATE POLICY esdata_all ON {table_name} TO esdata USING (true) WITH CHECK (true)';
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = '{table_name}'
                      AND policyname = 'service_role_all'
                ) THEN
                    EXECUTE 'CREATE POLICY service_role_all ON {table_name} TO service_role USING (true) WITH CHECK (true)';
                END IF;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    op.create_table(
        "perfil_entidad",
        sa.Column("codigo", sa.String(length=50), primary_key=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("supervisor", sa.String(length=20), nullable=False),
        sa.Column("regimen_primario", sa.String(length=100), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notas", sa.Text(), nullable=True),
    )

    op.create_table(
        "obligacion_perfil",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "perfil_codigo",
            sa.String(length=50),
            sa.ForeignKey("perfil_entidad.codigo"),
            nullable=False,
        ),
        sa.Column("obligacion_tipo", sa.String(length=50), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("periodicidad", sa.String(length=30), nullable=True),
        sa.Column("plazo_descripcion", sa.Text(), nullable=True),
        sa.Column("modelo_aeat", sa.String(length=10), nullable=True),
        sa.Column("norma_codigo", sa.String(length=50), nullable=True),
        sa.Column("articulo_referencia", sa.Text(), nullable=True),
        sa.Column("fuente_secundaria", sa.Text(), nullable=True),
        sa.Column("evidencia_tipo", sa.String(length=30), nullable=True),
        sa.Column("safe_to_answer", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completeness", sa.String(length=20), nullable=False, server_default="parcial"),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("capture_date", sa.Date(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "periodicidad IS NULL OR periodicidad IN "
            "('diaria','mensual','trimestral','semestral','anual','ad_hoc','continua')",
            name="ck_obligacion_perfil_periodicidad",
        ),
        sa.CheckConstraint(
            "completeness IN ('parcial','completa','evidence_limited')",
            name="ck_obligacion_perfil_completeness",
        ),
        sa.CheckConstraint("source_url <> ''", name="ck_obligacion_perfil_source_url"),
        sa.UniqueConstraint(
            "perfil_codigo",
            "obligacion_tipo",
            "descripcion",
            name="uq_obligacion_perfil_perfil_tipo_desc",
        ),
    )

    op.create_table(
        "obligacion_fuente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "obligacion_id",
            sa.Integer(),
            sa.ForeignKey("obligacion_perfil.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fuente_tipo", sa.String(length=30), nullable=False),
        sa.Column("codigo_referencia", sa.Text(), nullable=True),
        sa.Column("articulo", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("peso", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("source_url <> ''", name="ck_obligacion_fuente_source_url"),
        sa.CheckConstraint("peso >= 1", name="ck_obligacion_fuente_peso"),
    )

    op.create_index(
        "idx_obligacion_perfil_perfil_tipo",
        "obligacion_perfil",
        ["perfil_codigo", "obligacion_tipo"],
    )
    op.create_index("idx_obligacion_perfil_modelo_aeat", "obligacion_perfil", ["modelo_aeat"])
    op.create_index("idx_obligacion_perfil_norma_codigo", "obligacion_perfil", ["norma_codigo"])
    op.create_index("idx_obligacion_fuente_obligacion", "obligacion_fuente", ["obligacion_id"])

    for table_name in RLS_TABLES:
        _enable_rls(table_name)


def downgrade() -> None:
    op.drop_index("idx_obligacion_fuente_obligacion", table_name="obligacion_fuente")
    op.drop_index("idx_obligacion_perfil_norma_codigo", table_name="obligacion_perfil")
    op.drop_index("idx_obligacion_perfil_modelo_aeat", table_name="obligacion_perfil")
    op.drop_index("idx_obligacion_perfil_perfil_tipo", table_name="obligacion_perfil")
    op.drop_table("obligacion_fuente")
    op.drop_table("obligacion_perfil")
    op.drop_table("perfil_entidad")
