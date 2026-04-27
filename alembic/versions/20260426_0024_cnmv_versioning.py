"""Alembic migration — CNMV document versioning (Fase 23.6).

Crea tabla `documento_cnmv_version` con historial de cambios de documentos CNMV:
- tracking de versiones por referencia de documento
- estados: nuevo, modificado, derogado, sustituido
- auditoria con fecha y fuente de cada version

No modifica estructura de tablas existentes ni seed data.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0024_cnmv_versioning"
down_revision = "20260426_0023_cnmv_enriched_metadata"
branch_labels = None
depends_on = None


def upgrade():
    # Create CNMV document versioning table
    op.create_table(
        'documento_cnmv_version',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('documento_referencia', sa.Text(), nullable=False,
                  comment='Referencia del documento CNMV (FK logico a documento_interpretativo.referencia)'),
        sa.Column('version_numero', sa.Integer(), nullable=False,
                  comment='Numero de version (1, 2, 3...)'),
        sa.Column('estado_version', sa.Text(), nullable=False,
                  comment='Estado de la version: vigente, modificado, derogado, sustituido'),
        sa.Column('fecha_version', sa.Date(), nullable=False,
                  comment='Fecha de esta version'),
        sa.Column('resumen_cambios', sa.Text(), nullable=True,
                  comment='Resumen de cambios respecto a version anterior'),
        sa.Column('fuente_version', sa.Text(), nullable=True,
                  comment='URL o referencia de la fuente de esta version'),
        sa.Column('creado_en', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='Timestamp de creacion del registro'),
        sa.UniqueConstraint('documento_referencia', 'version_numero',
                            name='uq_documento_cnmv_version_ref_num'),
        sa.Index('idx_documento_cnmv_version_ref', 'documento_referencia'),
        sa.Index('idx_documento_cnmv_version_estado', 'estado_version'),
        sa.Index('idx_documento_cnmv_version_fecha', 'fecha_version'),
    )


def downgrade():
    op.drop_table('documento_cnmv_version')
