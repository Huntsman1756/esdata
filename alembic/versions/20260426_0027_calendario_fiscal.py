"""modelo_fiscal_calendar

Crea tabla para fechas reales de presentacion por modelo y campana.
"""

from alembic import op

revision = "20260426_0027_calendario_fiscal"
down_revision = "20260426_0026_irs_fiscal_compliance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "modelo_fiscal_calendar",
        op.Column("id", op.Integer(), primary_key=True),
        op.Column(
            "campana_id",
            op.Integer(),
            nullable=False,
            foreign_key=[
                "modelo_campana.id",
            ],
            ondelete="CASCADE",
        ),
        op.Column("fecha_inicio_presentacion", op.DateTime(), nullable=False),
        op.Column("fecha_fin_presentacion", op.DateTime(), nullable=False),
        op.Column("fecha_fin_prorroga", op.DateTime(), nullable=True),
        op.Column("observaciones", op.Text(), nullable=True),
        op.Column("fuente", op.Text(), nullable=True),
        op.Column("activo", op.Boolean(), nullable=False, server_default="true"),
        op.UniqueConstraint(
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
