"""Alembic migration — CNMV obligation links.

Crea tabla `cnmv_obligation_link` para mapear circulares CNMV a tipos de obligacion:
- `id`: PK autoincremental
- `documento_referencia`: FK a documento_interpretativo.referencia
- `tipo_obligacion`: tipo de obligacion (presentacion_modelo, remision_informacion, control_interno, comunicacion_indicio, reporting_prudencial)
- `nota`: descripcion de la obligacion

Soporta derivacion automatica de obligaciones desde textos de documentos CNMV.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0026_cnmv_obligation_links"
down_revision = "20260426_0025_cnmv_regulation_links"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cnmv_obligation_link',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('documento_referencia', sa.Text(), nullable=False),
        sa.Column('tipo_obligacion', sa.Text(), nullable=False),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['documento_referencia'],
            ['documento_interpretativo.referencia'],
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint('documento_referencia', 'tipo_obligacion', name='uq_cnmv_obligation_link')
    )

    op.create_index(
        'idx_cnmv_obligation_link_tipo',
        'cnmv_obligation_link',
        ['tipo_obligacion']
    )


def downgrade():
    op.drop_index('idx_cnmv_obligation_link_tipo', table_name='cnmv_obligation_link')
    op.drop_table('cnmv_obligation_link')
