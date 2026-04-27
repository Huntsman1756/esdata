"""irs_modelo

Crea tabla para modelos fiscales del IRS (Internal Revenue Service) US.

Equivalente a `aeat_modelo` para el ecosistema fiscal de EE.UU.

"""

from alembic import op
import sqlalchemy as sa

revision = "20260426_0029_irs_modelo"
down_revision = "20260426_0028_irnr_worker_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "irs_modelo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.Text(), nullable=False, unique=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("periodo", sa.Text(), nullable=True),
        sa.Column("impuesto", sa.Text(), nullable=True),
        sa.Column("url_info", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("actualizado_en", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_irs_modelo_impuesto",
        "irs_modelo",
        ["impuesto"],
    )
    op.create_index(
        "idx_irs_modelo_periodo",
        "irs_modelo",
        ["periodo"],
    )


def downgrade() -> None:
    op.drop_index("idx_irs_modelo_periodo", table_name="irs_modelo")
    op.drop_index("idx_irs_modelo_impuesto", table_name="irs_modelo")
    op.drop_table("irs_modelo")
