"""add hierarchy columns to modelo_clave

Revision ID: 20260602_0112_modelo_clave_hierarchy_schema
Revises: 20260601_0111_aeat_190_perception_keys_expansion
Create Date: 2026-06-02

Prepare modelo_clave for explicit key -> subkey relationships. Existing rows
remain top-level keys with parent_id=NULL and nivel=1. This structural
revision does not load subclave rows.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260602_0112_modelo_clave_hierarchy_schema"
down_revision = "20260601_0111_aeat_190_perception_keys_expansion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "modelo_clave",
        sa.Column("parent_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "modelo_clave",
        sa.Column("nivel", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.create_foreign_key(
        "modelo_clave_parent_id_fkey",
        "modelo_clave",
        "modelo_clave",
        ["parent_id"],
        ["id"],
    )
    op.create_index("ix_modelo_clave_parent_id", "modelo_clave", ["parent_id"])

    op.drop_constraint(
        "modelo_clave_campana_id_codigo_key",
        "modelo_clave",
        type_="unique",
    )
    op.drop_index("ux_modelo_clave_campana_tipo_codigo", table_name="modelo_clave")

    op.execute(
        """
        CREATE UNIQUE INDEX ux_modelo_clave_principal
        ON modelo_clave (campana_id, tipo, codigo)
        WHERE parent_id IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ux_modelo_clave_subclave
        ON modelo_clave (campana_id, parent_id, tipo, codigo)
        WHERE parent_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_modelo_clave_principal")
    op.execute("DROP INDEX IF EXISTS ux_modelo_clave_subclave")

    op.drop_index("ix_modelo_clave_parent_id", table_name="modelo_clave")
    op.drop_constraint(
        "modelo_clave_parent_id_fkey",
        "modelo_clave",
        type_="foreignkey",
    )
    op.drop_column("modelo_clave", "parent_id")
    op.drop_column("modelo_clave", "nivel")

    op.create_unique_constraint(
        "modelo_clave_campana_id_codigo_key",
        "modelo_clave",
        ["campana_id", "codigo"],
    )
    op.create_index(
        "ux_modelo_clave_campana_tipo_codigo",
        "modelo_clave",
        ["campana_id", "tipo", "codigo"],
        unique=True,
    )
