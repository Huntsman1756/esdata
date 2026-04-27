"""Alembic migration — CNMV enriched metadata columns.

Agrega columnas de enriquecimiento a `documento_interpretativo` para soportar
la expansion integral de la fuente CNMV (Fase 23.5):
- `numero_circular` TEXT: numero identificador de la circular CNMV (ej: '9/2008')
- `fecha_publicacion` TEXT: fecha de publicacion en BOE (ej: '2009', '2009-01-02')
- `referencia_boe` TEXT: referencia oficial BOE (ej: 'BOE-A-2009-133')
- `estado_vigencia` TEXT: estado actual del documento ('vigente', 'derogado', 'modificado')
- `ambito_tematico` TEXT: ambito tematico especifico para CNMV (ej: 'mifid_ii', 'mar', 'dora')
- `regulacion_relacionada` TEXT: regulacion EU/ES relacionada (ej: 'mifid_ii', 'mar', 'dora')

No modifica estructura de tablas existentes ni seed data.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0023_cnmv_enriched_metadata"
down_revision = "20260426_0022_micro_obligaciones_expansion"
branch_labels = None
depends_on = None


def upgrade():
    # Add CNMV enriched metadata columns
    op.add_column(
        'documento_interpretativo',
        sa.Column('numero_circular', sa.Text(), nullable=True)
    )
    op.add_column(
        'documento_interpretativo',
        sa.Column('fecha_publicacion', sa.Text(), nullable=True)
    )
    op.add_column(
        'documento_interpretativo',
        sa.Column('referencia_boe', sa.Text(), nullable=True)
    )
    op.add_column(
        'documento_interpretativo',
        sa.Column('estado_vigencia', sa.Text(), nullable=True)
    )
    op.add_column(
        'documento_interpretativo',
        sa.Column('ambito_tematico', sa.Text(), nullable=True)
    )
    op.add_column(
        'documento_interpretativo',
        sa.Column('regulacion_relacionada', sa.Text(), nullable=True)
    )

    # Create indexes for CNMV enriched columns
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_interpretativo_referencia_boe
        ON documento_interpretativo (referencia_boe)
        WHERE referencia_boe IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_interpretativo_estado_vigencia
        ON documento_interpretativo (estado_vigencia)
        WHERE estado_vigencia IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_interpretativo_regulacion_relacionada
        ON documento_interpretativo (regulacion_relacionada)
        WHERE regulacion_relacionada IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_interpretativo_ambito_tematico
        ON documento_interpretativo (ambito_tematico)
        WHERE ambito_tematico IS NOT NULL
        """
    )


def downgrade():
    # Remove indexes
    op.execute(
        """
        DROP INDEX IF EXISTS idx_documento_interpretativo_ambito_tematico
        """
    )
    op.execute(
        """
        DROP INDEX IF EXISTS idx_documento_interpretativo_regulacion_relacionada
        """
    )
    op.execute(
        """
        DROP INDEX IF EXISTS idx_documento_interpretativo_estado_vigencia
        """
    )
    op.execute(
        """
        DROP INDEX IF EXISTS idx_documento_interpretativo_referencia_boe
        """
    )

    # Remove columns
    op.drop_column('documento_interpretativo', 'regulacion_relacionada')
    op.drop_column('documento_interpretativo', 'ambito_tematico')
    op.drop_column('documento_interpretativo', 'estado_vigencia')
    op.drop_column('documento_interpretativo', 'referencia_boe')
    op.drop_column('documento_interpretativo', 'fecha_publicacion')
    op.drop_column('documento_interpretativo', 'numero_circular')
