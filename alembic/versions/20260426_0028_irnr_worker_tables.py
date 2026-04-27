"""irnr_worker_tables

Crea tablas para el worker IRNR (Impuesto sobre la Renta de No Residentes):
- `irnr_withholding_rate`: tipos de retencion IRNR por modelo y tipo de renta
- `irnr_instruccion`: instrucciones extraidas de paginas de modelos IRNR

"""

from alembic import op
import sqlalchemy as sa

revision = "20260426_0028_irnr_worker_tables"
down_revision = "20260426_0027_calendario_fiscal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- irnr_withholding_rate ---
    op.create_table(
        "irnr_withholding_rate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "modelo_id",
            sa.Integer(),
            sa.ForeignKey("aeat_modelo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo_renta", sa.Text(), nullable=False),
        sa.Column("tipo_retencion", sa.Float(), nullable=False),
        sa.Column("articulo_referencia", sa.Text(), nullable=True),
        sa.Column("fuente_texto", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("actualizado_en", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index(
        "idx_irnr_rate_tipo_renta",
        "irnr_withholding_rate",
        ["tipo_renta"],
    )
    op.create_index(
        "idx_irnr_rate_modelo",
        "irnr_withholding_rate",
        ["modelo_id"],
    )
    op.create_unique_constraint(
        "uq_irnr_rate_modelo_renta",
        "irnr_withholding_rate",
        ["modelo_id", "tipo_renta"],
    )

    # --- irnr_instruccion ---
    op.create_table(
        "irnr_instruccion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "modelo_id",
            sa.Integer(),
            sa.ForeignKey("aeat_modelo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seccion", sa.Text(), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("actualizado_en", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index(
        "idx_irnr_instruccion_seccion",
        "irnr_instruccion",
        ["seccion"],
    )
    op.create_unique_constraint(
        "uq_irnr_instruccion_modelo_seccion",
        "irnr_instruccion",
        ["modelo_id", "seccion"],
    )


def downgrade() -> None:
    op.drop_table("irnr_instruccion")
    op.drop_table("irnr_withholding_rate")
