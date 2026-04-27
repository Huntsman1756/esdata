"""modelo_fiscal_calendar

Crea tabla para fechas reales de presentacion por modelo y campana.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0027_calendario_fiscal"
down_revision = "20260426_0026_irs_fiscal_compliance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "modelo_fiscal_calendar",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "campana_id",
            sa.Integer(),
            sa.ForeignKey("modelo_campana.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha_inicio_presentacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_fin_presentacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_fin_prorroga", sa.DateTime(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("fuente", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint(
            "campana_id",
            "fecha_inicio_presentacion",
            name="uq_calendario_campana_fecha",
        ),
    )
    op.create_index(
        "idx_calendario_fecha_fin",
        "modelo_fiscal_calendar",
        ["fecha_fin_presentacion"],
    )
    op.create_index(
        "idx_calendario_activo",
        "modelo_fiscal_calendar",
        ["activo"],
        postgresql_where="activo = true",
    )


def downgrade() -> None:
    op.drop_index("idx_calendario_activo", table_name="modelo_fiscal_calendar")
    op.drop_index("idx_calendario_fecha_fin", table_name="modelo_fiscal_calendar")
    op.drop_table("modelo_fiscal_calendar")
