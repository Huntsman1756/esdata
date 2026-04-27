"""Alembic migration — CNMV document versioning.

Crea tabla `documento_version` para historial de cambios en documentos CNMV:
- `id`: PK autoincremental
- `documento_referencia`: FK a documento_interpretativo.referencia
- `version_num`: numero de version (1, 2, 3...)
- `texto`: snapshot del texto completo
- `cambio_tipo`: 'creado', 'modificado', 'derogado', 'sustituido'
- `fecha_version`: fecha de la version
- `nota`: descripcion del cambio
- `url_version`: URL de la version en fuente original

Soporta versionado de circulares CNMV al ser modificadas o derogadas.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0024_cnmv_document_versioning"
down_revision = "20260426_0024_cnmv_versioning"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'documento_version',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('documento_referencia', sa.Text(), nullable=False),
        sa.Column('version_num', sa.Integer(), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('cambio_tipo', sa.Text(), nullable=False),
        sa.Column('fecha_version', sa.Text(), nullable=False),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.Column('url_version', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['documento_referencia'],
            ['documento_interpretativo.referencia'],
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint('documento_referencia', 'version_num', name='uq_documento_version_num')
    )

    op.create_index(
        'idx_documento_version_referencia',
        'documento_version',
        ['documento_referencia']
    )
    op.create_index(
        'idx_documento_version_cambio_tipo',
        'documento_version',
        ['cambio_tipo']
    )


def downgrade():
    op.drop_index('idx_documento_version_cambio_tipo', table_name='documento_version')
    op.drop_index('idx_documento_version_referencia', table_name='documento_version')
    op.drop_table('documento_version')
