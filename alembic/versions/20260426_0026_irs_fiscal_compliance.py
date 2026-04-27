"""Alembic migration — IRS & international fiscal compliance.

Crea tablas para el cumplimiento fiscal internacional:
- `irs_fiscal_norma`: normas IRS (publications, forms, instructions)
- `irs_dta_convention`: convenios de doble tributacion (DTA)
- `irs_withholding_rule`: reglas de retencion por tipo de renta
- `irs_w8_form`: formularios W-8 (W-8BEN, W-8BEN-E, W-8EXP, W-8ECF)
- `irs_tin_reference`: referencias TIN por pais
- `giin_registry`: registro GIIN/FFI/NFFE
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260426_0026_irs_fiscal_compliance"
down_revision = "20260426_0026_cnmv_obligation_links"
branch_labels = None
depends_on = None


def upgrade():
    # --- irs_fiscal_norma ---
    op.create_table(
        'irs_fiscal_norma',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo', sa.Text(), nullable=False, unique=True),
        sa.Column('titulo', sa.Text(), nullable=False),
        sa.Column('tipo', sa.Text(), nullable=False, server_default='publicacion'),
        sa.Column('anio_vigencia', sa.Integer(), nullable=True),
        sa.Column('texto', sa.Text(), nullable=True),
        sa.Column('url_fuente', sa.Text(), nullable=True),
        sa.Column('estado', sa.Text(), nullable=False, server_default='activo'),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text("NOW()")),
    )

    op.create_index(
        'idx_irs_fiscal_norma_tipo',
        'irs_fiscal_norma',
        ['tipo']
    )
    op.create_index(
        'idx_irs_fiscal_norma_anio',
        'irs_fiscal_norma',
        ['anio_vigencia']
    )

    # --- irs_dta_convention ---
    op.create_table(
        'irs_dta_convention',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo', sa.Text(), nullable=False, unique=True),
        sa.Column('pais_origen', sa.Text(), nullable=False),
        sa.Column('pais_destino', sa.Text(), nullable=False),
        sa.Column('titulo', sa.Text(), nullable=False),
        sa.Column('fecha_firma', sa.Date(), nullable=True),
        sa.Column('fecha_vigencia', sa.Date(), nullable=True),
        sa.Column('tipo_acuerdo', sa.Text(), nullable=False, server_default='bilateral'),
        sa.Column('boe_referencia', sa.Text(), nullable=True),
        sa.Column('articulos', JSONB, nullable=True),
        sa.Column('texto_completo', sa.Text(), nullable=True),
        sa.Column('estado', sa.Text(), nullable=False, server_default='vigente'),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text("NOW()")),
    )

    op.create_index(
        'idx_irs_dta_pais_origen',
        'irs_dta_convention',
        ['pais_origen']
    )
    op.create_index(
        'idx_irs_dta_pais_destino',
        'irs_dta_convention',
        ['pais_destino']
    )
    op.create_index(
        'idx_irs_dta_estado',
        'irs_dta_convention',
        ['estado']
    )

    # --- irs_withholding_rule ---
    op.create_table(
        'irs_withholding_rule',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo', sa.Text(), nullable=False, unique=True),
        sa.Column('tipo_renta', sa.Text(), nullable=False),
        sa.Column('tipo_renta_espanol', sa.Text(), nullable=True),
        sa.Column('tipo_retencion_default', sa.Float(), nullable=False, server_default='30.0'),
        sa.Column('tipo_retencion_dta', sa.Float(), nullable=True),
        sa.Column('pais_aplicable', sa.Text(), nullable=True),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('norma_referencia', sa.Text(), nullable=True),
        sa.Column('articulo_referencia', sa.Text(), nullable=True),
        sa.Column('estado', sa.Text(), nullable=False, server_default='activo'),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text("NOW()")),
    )

    op.create_index(
        'idx_irs_withholding_tipo_renta',
        'irs_withholding_rule',
        ['tipo_renta']
    )
    op.create_index(
        'idx_irs_withholding_pais',
        'irs_withholding_rule',
        ['pais_aplicable']
    )

    # --- irs_w8_form ---
    op.create_table(
        'irs_w8_form',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo', sa.Text(), nullable=False, unique=True),
        sa.Column('nombre', sa.Text(), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('tipo_sujeto', sa.Text(), nullable=False, server_default='persona_fisica'),
        sa.Column('finalidad', sa.Text(), nullable=True),
        sa.Column('partes', JSONB, nullable=True),
        sa.Column('validez_anios', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('obligacion_asociada', sa.Text(), nullable=True),
        sa.Column('texto_detalle', sa.Text(), nullable=True),
        sa.Column('estado', sa.Text(), nullable=False, server_default='activo'),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # --- irs_tin_reference ---
    op.create_table(
        'irs_tin_reference',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo_pais', sa.Text(), nullable=False),
        sa.Column('pais_nombre', sa.Text(), nullable=False),
        sa.Column('formato_tin', sa.Text(), nullable=True),
        sa.Column('ejemplo_tin', sa.Text(), nullable=True),
        sa.Column('emisor_espana', sa.Text(), nullable=True),
        sa.Column('emisor_pais', sa.Text(), nullable=True),
        sa.Column('es_ocde', sa.Boolean(), nullable=False, server_default='f'),
        sa.Column('es_eu_vat', sa.Boolean(), nullable=False, server_default='f'),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text("NOW()")),
    )

    op.create_index(
        'idx_irs_tin_pais',
        'irs_tin_reference',
        ['codigo_pais']
    )
    op.create_index(
        'idx_irs_tin_ocde',
        'irs_tin_reference',
        ['es_ocde']
    )

    # --- giin_registry ---
    op.create_table(
        'giin_registry',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('giin', sa.Text(), nullable=False, unique=True),
        sa.Column('entidad_nombre', sa.Text(), nullable=False),
        sa.Column('entidad_pais', sa.Text(), nullable=False),
        sa.Column('tipo_entidad', sa.Text(), nullable=False),
        sa.Column('estado_fatca', sa.Text(), nullable=False, server_default='activo'),
        sa.Column('fecha_registro', sa.Date(), nullable=True),
        sa.Column('fecha_expiracion', sa.Date(), nullable=True),
        sa.Column('es_exempt_beneficial_owner', sa.Boolean(), nullable=False, server_default='f'),
        sa.Column('es_sponsored_ffo', sa.Boolean(), nullable=False, server_default='f'),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text("NOW()")),
    )

    op.create_index(
        'idx_giin_estado',
        'giin_registry',
        ['estado_fatca']
    )
    op.create_index(
        'idx_giin_pais',
        'giin_registry',
        ['entidad_pais']
    )


def downgrade():
    op.drop_table('giin_registry')
    op.drop_table('irs_tin_reference')
    op.drop_table('irs_w8_form')
    op.drop_table('irs_withholding_rule')
    op.drop_table('irs_dta_convention')
    op.drop_table('irs_fiscal_norma')
