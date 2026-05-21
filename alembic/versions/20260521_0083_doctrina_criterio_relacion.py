"""add doctrina criterio relacion table

Revision ID: 20260521_0083_doctrina_criterio_relacion
Revises: 20260519_0082_documento_interpretativo_sujeto_obligado
Create Date: 2026-05-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260521_0083_doctrina_criterio_relacion"
down_revision = "20260519_0082_documento_interpretativo_sujeto_obligado"
branch_labels = None
depends_on = None


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
        "criterio_relacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("linea_codigo", sa.String(length=32), nullable=False),
        sa.Column(
            "linea_criterio_id",
            sa.Integer(),
            sa.ForeignKey("linea_criterio.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("documento_referencia", sa.Text(), nullable=False),
        sa.Column("norma_codigo", sa.String(length=64), nullable=True),
        sa.Column("articulo", sa.Text(), nullable=True),
        sa.Column("impuesto", sa.String(length=50), nullable=True),
        sa.Column("modelo_aeat", sa.String(length=20), nullable=True),
        sa.Column("tipo_renta", sa.String(length=100), nullable=True),
        sa.Column("relacion", sa.String(length=50), nullable=False),
        sa.Column("metodo_enlace", sa.String(length=50), nullable=False),
        sa.Column("confianza_enlace", sa.Numeric(3, 2), nullable=False, server_default="0"),
        sa.Column("nota_limitacion", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_hash", sa.Text(), nullable=True),
        sa.Column("capture_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completeness", sa.String(length=20), nullable=False, server_default="partial"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "completeness IN ('complete','partial','target','configured_but_unavailable','out_of_scope')",
            name="ck_criterio_relacion_completeness",
        ),
        sa.CheckConstraint(
            "confianza_enlace >= 0 AND confianza_enlace <= 1",
            name="ck_criterio_relacion_confianza_range",
        ),
        sa.UniqueConstraint(
            "linea_codigo",
            "documento_referencia",
            "modelo_aeat",
            "tipo_renta",
            "relacion",
            name="uq_criterio_relacion_linea_doc_modelo_tipo",
        ),
    )
    op.create_index("idx_criterio_relacion_linea_codigo", "criterio_relacion", ["linea_codigo"])
    op.create_index(
        "idx_criterio_relacion_linea_id",
        "criterio_relacion",
        ["linea_criterio_id"],
    )
    op.create_index(
        "idx_criterio_relacion_documento",
        "criterio_relacion",
        ["documento_referencia"],
    )
    op.create_index("idx_criterio_relacion_modelo", "criterio_relacion", ["modelo_aeat"])

    _enable_rls("criterio_relacion")

    op.execute(
        sa.text(
            """
            INSERT INTO criterio_relacion (
                linea_codigo, documento_referencia, norma_codigo, articulo,
                impuesto, modelo_aeat, tipo_renta, relacion, metodo_enlace,
                confianza_enlace, nota_limitacion, source_url, source_hash,
                capture_date, verified, completeness
            )
            SELECT
                'D-01',
                d.referencia,
                'TRLIRNR',
                '31',
                'IRNR',
                '216/296',
                'retenciones_no_residentes',
                'modelo_supuesto',
                'manual_official',
                1.00,
                'Curacion D-01: modelo 216/296 auditado por supuesto en texto oficial V0166-25',
                d.url_fuente,
                sr.content_hash_sha256,
                sr.fetched_at,
                true,
                'complete'
            FROM documento_interpretativo d
            JOIN source_revision sr
              ON sr.source_entity_id = d.referencia
             AND LOWER(sr.source_entity_tipo) IN (
                 'consulta', 'consulta_vinculante', 'documento', 'resolucion_teac'
             )
            WHERE d.referencia = 'V0166-25'
              AND d.url_fuente IS NOT NULL
              AND sr.content_hash_sha256 IS NOT NULL
              AND sr.fetched_at IS NOT NULL
            ON CONFLICT (linea_codigo, documento_referencia, modelo_aeat, tipo_renta, relacion)
            DO UPDATE SET
                source_url = EXCLUDED.source_url,
                source_hash = EXCLUDED.source_hash,
                capture_date = EXCLUDED.capture_date,
                verified = EXCLUDED.verified,
                completeness = EXCLUDED.completeness,
                updated_at = now()
            """
        )
    )


def downgrade() -> None:
    op.drop_index("idx_criterio_relacion_modelo", table_name="criterio_relacion")
    op.drop_index("idx_criterio_relacion_documento", table_name="criterio_relacion")
    op.drop_index("idx_criterio_relacion_linea_id", table_name="criterio_relacion")
    op.drop_index("idx_criterio_relacion_linea_codigo", table_name="criterio_relacion")
    op.drop_table("criterio_relacion")
