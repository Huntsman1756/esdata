"""obligacion_internacional

Crea tabla para obligaciones internacionales (FATCA, CRS, IGA, DAC).

"""

import sqlalchemy as sa
from alembic import op

revision = "20260426_0029_international_obligations"
down_revision = "20260426_0029_irs_modelo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "obligacion_internacional",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(50), nullable=False, unique=True),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("jurisdiccion_origen", sa.String(100), nullable=True),
        sa.Column("jurisdiccion_aplicacion", sa.String(100), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(50), nullable=False, server_default="activo"),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("actualizado_en", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index(
        "idx_obligacion_internacional_tipo",
        "obligacion_internacional",
        ["tipo"],
    )
    op.create_index(
        "idx_obligacion_internacional_estado",
        "obligacion_internacional",
        ["estado"],
        postgresql_where="estado = 'activo'",
    )
    op.create_index(
        "idx_obligacion_internacional_origen",
        "obligacion_internacional",
        ["jurisdiccion_origen"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_obligacion_internacional_origen",
        table_name="obligacion_internacional",
    )
    op.drop_index(
        "idx_obligacion_internacional_estado",
        table_name="obligacion_internacional",
    )
    op.drop_index(
        "idx_obligacion_internacional_tipo",
        table_name="obligacion_internacional",
    )
    op.drop_table("obligacion_internacional")
