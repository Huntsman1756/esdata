"""add created_at/updated_at to articulo and version_articulo (A-09)

Revision ID: 20260509_0063_articulo_timestamps
Revises: 20260509_0062_rls_modelo_recurso
Create Date: 2026-05-09

Temporal auditability for legal citations — a lawyer citing an article in
court must be able to prove when the data was obtained and when it was last
refreshed. Prior to this migration `articulo` and `version_articulo` had no
timestamps at all.

The trigger `articulo_set_updated_at` keeps updated_at fresh on any UPDATE
without requiring the worker to set it explicitly.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260509_0063_articulo_timestamps"
down_revision = "20260509_0062_rls_modelo_recurso"
branch_labels = None
depends_on = None


TRIGGER_FN_SQL = """
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    # Guard function (idempotent — may already exist from other tables).
    op.execute(TRIGGER_FN_SQL)

    # articulo
    op.add_column(
        "articulo",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.add_column(
        "articulo",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_articulo_updated_at ON articulo;
        CREATE TRIGGER trg_articulo_updated_at
        BEFORE UPDATE ON articulo
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )

    # version_articulo
    op.add_column(
        "version_articulo",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.add_column(
        "version_articulo",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_version_articulo_updated_at ON version_articulo;
        CREATE TRIGGER trg_version_articulo_updated_at
        BEFORE UPDATE ON version_articulo
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_version_articulo_updated_at ON version_articulo;")
    op.execute("DROP TRIGGER IF EXISTS trg_articulo_updated_at ON articulo;")
    op.drop_column("version_articulo", "updated_at")
    op.drop_column("version_articulo", "created_at")
    op.drop_column("articulo", "updated_at")
    op.drop_column("articulo", "created_at")
    # Do NOT drop set_updated_at — other tables may depend on it.
