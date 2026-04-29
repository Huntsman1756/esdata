"""add ownership tables for corporate structure and beneficial ownership

Creates ownership_share, ownership_relation and ubo_record tables
to model corporate ownership, participations and beneficial ownership
with temporal versioning and source traceability.

# Revision ID: 20260426_0013_ownership
# Revises: 20260426_0012_screening
# Create Date: 2026-04-26 00:00:00

"""

from alembic import op

revision = "20260426_0013_ownership"
down_revision = "20260426_0012_screening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ownership_share — participaciones directas entre entidades
    op.execute(
        """
        CREATE TABLE ownership_share (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresa(id),
            titular_id INTEGER NOT NULL,
            titular_tipo TEXT NOT NULL CHECK (titular_tipo IN ('empresa', 'persona')),
            titular_nombre TEXT NOT NULL,
            porcentaje NUMERIC(5,2) NOT NULL,
            tipo_participacion TEXT NOT NULL DEFAULT 'directa' CHECK (tipo_participacion IN ('directa', 'indirecta')),
            vigencia_desde TEXT,
            vigencia_hasta TEXT,
            fuente TEXT NOT NULL,
            fuente_ref TEXT,
            documento_id INTEGER REFERENCES documento_interpretativo(id),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ownership_share_empresa
            ON ownership_share(empresa_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ownership_share_titular
            ON ownership_share(titular_nombre)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ownership_share_fuente
            ON ownership_share(fuente)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ownership_share_vigencia
            ON ownership_share(vigencia_desde, vigencia_hasta)
        """
    )

    # ownership_relation — relaciones societarias (control, absorbente, absorbida, etc.)
    op.execute(
        """
        CREATE TABLE ownership_relation (
            id SERIAL PRIMARY KEY,
            empresa_origen_id INTEGER NOT NULL REFERENCES empresa(id),
            empresa_destino_id INTEGER NOT NULL REFERENCES empresa(id),
            tipo_relacion TEXT NOT NULL CHECK (tipo_relacion IN (
                'control', 'participacion_mayoritaria', 'participacion_significativa',
                'absorbente', 'absorbida', 'escindente', 'escindida',
                'filial', 'matriz', 'equivalencia', 'joint_venture',
                'representante_legal', 'administrador', 'grupo_economico'
            )),
            porcentaje NUMERIC(5,2),
            vigencia_desde TEXT,
            vigencia_hasta TEXT,
            fuente TEXT NOT NULL,
            fuente_ref TEXT,
            documento_id INTEGER REFERENCES documento_interpretativo(id),
            nota TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_origen_id, empresa_destino_id, tipo_relacion, vigencia_desde)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ownership_relation_origen
            ON ownership_relation(empresa_origen_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ownership_relation_destino
            ON ownership_relation(empresa_destino_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ownership_relation_tipo
            ON ownership_relation(tipo_relacion)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ownership_relation_fuente
            ON ownership_relation(fuente)
        """
    )

    # ubo_record — beneficial ownership records
    op.execute(
        """
        CREATE TABLE ubo_record (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresa(id),
            nombre_persona TEXT NOT NULL,
            nacionalidad TEXT,
            fecha_nacimiento TEXT,
            pais_residencia TEXT,
            tipo_ubo TEXT NOT NULL CHECK (tipo_ubo IN (
                'titular_poder', 'titular_propiedad', 'control_por_otros_medios',
                'administrador_legal', 'representante'
            )),
            porcentaje_control NUMERIC(5,2),
            umbral_superado TEXT,
            vigencia_desde TEXT,
            vigencia_hasta TEXT,
            fuente TEXT NOT NULL,
            fuente_ref TEXT,
            documento_id INTEGER REFERENCES documento_interpretativo(id),
            nota TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ubo_record_empresa
            ON ubo_record(empresa_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ubo_record_nombre
            ON ubo_record(nombre_persona)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ubo_record_tipo
            ON ubo_record(tipo_ubo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ubo_record_fuente
            ON ubo_record(fuente)
        """
    )


def downgrade() -> None:
    op.drop_table("ubo_record")
    op.drop_table("ownership_relation")
    op.drop_table("ownership_share")
