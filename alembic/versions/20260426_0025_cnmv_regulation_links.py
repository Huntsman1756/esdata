"""Alembic migration — CNMV regulation links.

Crea tabla `cnmv_regulation_link` para mapear circulares CNMV a regulaciones EU/ES:
- `id`: PK autoincremental
- `documento_referencia`: FK a documento_interpretativo.referencia
- `regulacion_id`: identificador de regulacion (ej: 'mifid_ii', 'mar', 'dora', 'priips', 'livmc')
- `relacion_tipo`: tipo de relacion ('implementa', 'deriva_de', 'complementa', 'transpone')
- `nota`: descripcion de la relacion

Soporta navegacion CNMV <-> regulaciones EU y leyes ES.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0025_cnmv_regulation_links"
down_revision = "20260426_0024_cnmv_document_versioning"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cnmv_regulation_link',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('documento_referencia', sa.Text(), nullable=False),
        sa.Column('regulacion_id', sa.Text(), nullable=False),
        sa.Column('relacion_tipo', sa.Text(), nullable=False, server_default=sa.text("'implementa'::text")),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['documento_referencia'],
            ['documento_interpretativo.referencia'],
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint('documento_referencia', 'regulacion_id', name='uq_cnmv_regulation_link')
    )

    op.create_index(
        'idx_cnmv_regulation_link_regulacion',
        'cnmv_regulation_link',
        ['regulacion_id']
    )


def downgrade():
    op.drop_index('idx_cnmv_regulation_link_regulacion', table_name='cnmv_regulation_link')
    op.drop_table('cnmv_regulation_link')
