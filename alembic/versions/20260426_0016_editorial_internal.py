"""add nota_editorial_interna and posicion_interpretativa tables

Creates editorial notes and interpretive position tables for Fase 18
(Capa editorial interna y criterio experto):

- nota_editorial_interna: internal editorial notes linked to official sources
- posicion_interpretativa: versioned internal interpretive positions

# Revision ID: 20260426_0016_editorial_internal
# Revises: 20260426_0015_pgc_xbrl_mapping
# Create Date: 2026-04-26 00:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "20260426_0016_editorial_internal"
down_revision = "20260426_0015_pgc_xbrl_mapping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nota_editorial_interna",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("resumen_ejecutivo", sa.Text(), nullable=True),
        sa.Column("contexto", sa.Text(), nullable=True),
        sa.Column("impacto_practico", sa.Text(), nullable=True),
        sa.Column("advertencias", sa.Text(), nullable=True),
        sa.Column("fuente_oficial_referencia", sa.Text(), nullable=True,
                   comment="Referencia al documento oficial (ej: BOE-A-2009-133)"),
        sa.Column("documento_origen_id", sa.Integer(), nullable=True,
                   comment="FK a documento_interpretativo.id"),
        sa.Column("autor_id", sa.Text(), nullable=False,
                   comment="Identificador del autor interno"),
        sa.Column("revisor_id", sa.Text(), nullable=True,
                   comment="Identificador del revisor interno"),
        sa.Column("estado", sa.Text(), nullable=False, server_default=sa.text("'borrador'::text"),
                   comment="borrador, vigente, revisar, obsoleto"),
        sa.Column("tipo_contenido", sa.Text(), nullable=False, server_default=sa.text("'resumen_interno'::text"),
                   comment="resumen_interno, criterio_experto, nota_operativa"),
        sa.Column("fecha_creacion", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("fecha_revision", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["documento_origen_id"], ["documento_interpretativo.id"], ondelete="SET NULL"),
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nota_editorial_estado
            ON nota_editorial_interna(estado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nota_editorial_fuente
            ON nota_editorial_interna(fuente_oficial_referencia)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nota_editorial_origen
            ON nota_editorial_interna(documento_origen_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nota_editorial_autor
            ON nota_editorial_interna(autor_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nota_editorial_tipo
            ON nota_editorial_interna(tipo_contenido)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nota_editorial_texto_trgm
            ON nota_editorial_interna USING gin (titulo gin_trgm_ops)
        """
    )

    op.create_table(
        "posicion_interpretativa",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("contenido", sa.Text(), nullable=True),
        sa.Column("fuente_oficial_referencia", sa.Text(), nullable=True,
                   comment="Referencia al documento oficial (ej: BOE-A-2009-133)"),
        sa.Column("documento_origen_id", sa.Integer(), nullable=True,
                   comment="FK a documento_interpretativo.id"),
        sa.Column("autor_id", sa.Text(), nullable=False,
                   comment="Identificador del autor interno"),
        sa.Column("revisor_id", sa.Text(), nullable=True,
                   comment="Identificador del revisor interno"),
        sa.Column("estado", sa.Text(), nullable=False, server_default=sa.text("'borrador'::text"),
                   comment="borrador, vigente, revisar, obsoleto"),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("vigencia_desde", sa.Date(), nullable=True),
        sa.Column("vigencia_hasta", sa.Date(), nullable=True),
        sa.Column("version_anterior_id", sa.dialects.postgresql.UUID(), nullable=True,
                   comment="FK a posicion_interpretativa.id de version anterior"),
        sa.Column("fecha_creacion", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("fecha_revision", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["documento_origen_id"], ["documento_interpretativo.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["version_anterior_id"], ["posicion_interpretativa.id"]),
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posicion_interpretativa_estado
            ON posicion_interpretativa(estado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posicion_interpretativa_fuente
            ON posicion_interpretativa(fuente_oficial_referencia)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posicion_interpretativa_origen
            ON posicion_interpretativa(documento_origen_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posicion_interpretativa_version
            ON posicion_interpretativa(documento_origen_id, version)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posicion_interpretativa_autor
            ON posicion_interpretativa(autor_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_posicion_interpretativa_texto_trgm
            ON posicion_interpretativa USING gin (titulo gin_trgm_ops)
        """
    )

    # Seed: editorial note for CNMV circular 9/2008
    op.execute(
        """
        INSERT INTO nota_editorial_interna (
            titulo, resumen_ejecutivo, contexto, impacto_practico,
            fuente_oficial_referencia, documento_origen_id,
            autor_id, estado, tipo_contenido
        )
        SELECT
            'Resumen operativo: Circular CNMV 9/2008',
            'Normas contables y estados de información para entidades supervisadas. Define los estados de información reservada y pública.',
            'Aplicable a todas las sociedades de valores. Complementa el PGC con requisitos específicos de reporting prudencial.',
            'Las sociedades de valores deben preparar estados de información reservada adicionales a las cuentas anuales PGC.',
            'BOE-A-2009-133',
            (SELECT id FROM documento_interpretativo WHERE referencia = 'BOE-A-2009-133' LIMIT 1),
            'compliance',
            'vigente',
            'resumen_interno'
        WHERE EXISTS (SELECT 1 FROM documento_interpretativo WHERE referencia = 'BOE-A-2009-133')
        """
    )

    # Seed: interpretive position on MiFID II suitability
    op.execute(
        """
        INSERT INTO posicion_interpretativa (
            titulo, descripcion, contenido, fuente_oficial_referencia,
            autor_id, estado, version, vigencia_desde
        )
        SELECT
            'Criterio interno: adecuación MiFID II para servicios de inversión',
            'Criterio interno sobre la aplicacion del requisito de adecuación (suitability) de MiFID II en servicios de asesoria de inversion.',
            'Para la prestacion de servicios de asesoria de inversion, se requiere documentar la adecuación de la recomendacion al perfil del cliente. La documentacion debe incluir: (a) datos sobre conocimientos y experiencia del cliente, (b) informacion sobre situacion financiera, (c) objetivos de inversion. Se considera cumplimiento minimo la firma del cuestionario de adecuacion estandarizado.',
            'eurl:2014:65',
            'compliance',
            'vigente',
            1,
            '2026-05-01'::date
        """
    )


def downgrade() -> None:
    op.drop_table("posicion_interpretativa")
    op.drop_table("nota_editorial_interna")
