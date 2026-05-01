"""aeat modelo recurso versioning

Extiende el esquema AEAT para soportar versionado de recursos oficiales por
campana (PDF/HTML/diseno/normativa/etc.) con deteccion por hash.

Esta migracion mergea los dos heads actuales y deja un unico head nuevo.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


revision = "20260501_0054_aeat_modelo_recurso"
down_revision = (
    "20260429_0003_corpus_verificada",
    "20260501_0053_absorb_runtime_table_drift",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "aeat_modelo",
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column("aeat_modelo", sa.Column("url_listado", sa.Text(), nullable=True))
    op.add_column("aeat_modelo", sa.Column("slug_portal", sa.Text(), nullable=True))
    op.add_column("aeat_modelo", sa.Column("derogado_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "aeat_modelo",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.add_column(
        "modelo_campana",
        sa.Column("fecha_publicacion_portal", sa.Date(), nullable=True),
    )
    op.add_column(
        "modelo_campana",
        sa.Column("fecha_actualizacion_portal", sa.Date(), nullable=True),
    )
    op.add_column(
        "modelo_campana",
        sa.Column("estado_publicacion", sa.Text(), nullable=True),
    )
    op.add_column(
        "modelo_campana",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "modelo_recurso",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "campana_id",
            sa.Integer(),
            sa.ForeignKey("modelo_campana.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo_recurso", sa.Text(), nullable=False),
        sa.Column("formato", sa.Text(), nullable=False),
        sa.Column("url_recurso", sa.Text(), nullable=False),
        sa.Column("sha256_contenido", sa.Text(), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified", sa.Text(), nullable=True),
        sa.Column("content_length", sa.BigInteger(), nullable=True),
        sa.Column("fecha_publicacion_recurso", sa.Date(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "campana_id",
            "tipo_recurso",
            "sha256_contenido",
            name="uq_modelo_recurso_hash",
        ),
    )
    op.create_index(
        "idx_modelo_recurso_campana_tipo",
        "modelo_recurso",
        ["campana_id", "tipo_recurso"],
    )
    op.create_index(
        "idx_modelo_recurso_sha256",
        "modelo_recurso",
        ["sha256_contenido"],
    )
    op.create_index(
        "idx_modelo_recurso_activa_unica",
        "modelo_recurso",
        ["campana_id", "tipo_recurso"],
        unique=True,
        postgresql_where=sa.text("activa = true"),
    )


def downgrade() -> None:
    op.drop_index("idx_modelo_recurso_activa_unica", table_name="modelo_recurso")
    op.drop_index("idx_modelo_recurso_sha256", table_name="modelo_recurso")
    op.drop_index("idx_modelo_recurso_campana_tipo", table_name="modelo_recurso")
    op.drop_table("modelo_recurso")

    op.drop_column("modelo_campana", "updated_at")
    op.drop_column("modelo_campana", "estado_publicacion")
    op.drop_column("modelo_campana", "fecha_actualizacion_portal")
    op.drop_column("modelo_campana", "fecha_publicacion_portal")

    op.drop_column("aeat_modelo", "updated_at")
    op.drop_column("aeat_modelo", "derogado_at")
    op.drop_column("aeat_modelo", "slug_portal")
    op.drop_column("aeat_modelo", "url_listado")
    op.drop_column("aeat_modelo", "activo")
