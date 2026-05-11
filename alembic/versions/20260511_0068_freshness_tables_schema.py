"""own freshness monitoring tables in Alembic

Revision ID: 20260511_0068_freshness_tables_schema
Revises: 20260510_0067_monitoring_rls_closure
Create Date: 2026-05-11

The API can still tolerate pre-existing deployments where these tables were
created by init/runtime compatibility code. This migration makes the durable
schema explicit in Alembic and applies the same backend-only RLS policies.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260511_0068_freshness_tables_schema"
down_revision = "20260510_0067_monitoring_rls_closure"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return table_name in sa.inspect(bind).get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _ensure_rls(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE IF EXISTS {table_name} ENABLE ROW LEVEL SECURITY;"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS esdata_all ON {table_name};"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY esdata_all ON {table_name}
                TO esdata
                USING (true)
                WITH CHECK (true);
            """
        )
    )
    op.execute(sa.text(f"DROP POLICY IF EXISTS service_role_all ON {table_name};"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY service_role_all ON {table_name}
                TO service_role
                USING (true)
                WITH CHECK (true);
            """
        )
    )


def upgrade() -> None:
    if not _table_exists("source_freshness_snapshot"):
        op.create_table(
            "source_freshness_snapshot",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("snapshot_id", sa.Text(), nullable=False, unique=True),
            sa.Column("source_id", sa.Text(), nullable=False),
            sa.Column("snapshot_version", sa.Text(), nullable=False),
            sa.Column("snapshot_at", sa.Text(), nullable=False),
            sa.Column("last_success_at", sa.Text(), nullable=True),
            sa.Column("last_status", sa.Text(), nullable=False),
            sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("cadencia", sa.Text(), nullable=False),
            sa.Column("modo_deteccion_cambios", sa.Text(), nullable=False),
            sa.Column("manifest_hash", sa.Text(), nullable=False, server_default=""),
            sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
        )
    if not _index_exists("source_freshness_snapshot", "idx_source_snapshot_source"):
        op.create_index(
            "idx_source_snapshot_source",
            "source_freshness_snapshot",
            ["source_id", "snapshot_at"],
        )
    if not _index_exists("source_freshness_snapshot", "idx_source_snapshot_version"):
        op.create_index(
            "idx_source_snapshot_version",
            "source_freshness_snapshot",
            ["snapshot_version"],
        )
    _ensure_rls("source_freshness_snapshot")

    if not _table_exists("data_freshness_alerts"):
        op.create_table(
            "data_freshness_alerts",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("alert_id", sa.Text(), nullable=False, unique=True),
            sa.Column("source_id", sa.Text(), nullable=False),
            sa.Column("alert_level", sa.Text(), nullable=False),
            sa.Column("stale_since", sa.Text(), nullable=True),
            sa.Column("expected_interval", sa.Text(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False, server_default=""),
            sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.Text(), nullable=False),
            sa.Column("resolved_at", sa.Text(), nullable=True),
        )
    if not _index_exists("data_freshness_alerts", "idx_freshness_alerts_source"):
        op.create_index(
            "idx_freshness_alerts_source",
            "data_freshness_alerts",
            ["source_id", "stale_since"],
        )
    if not _index_exists("data_freshness_alerts", "idx_freshness_alerts_level"):
        op.create_index(
            "idx_freshness_alerts_level",
            "data_freshness_alerts",
            ["alert_level", "acknowledged"],
        )
    _ensure_rls("data_freshness_alerts")


def downgrade() -> None:
    for table_name in ("data_freshness_alerts", "source_freshness_snapshot"):
        if not _table_exists(table_name):
            continue
        op.execute(sa.text(f"DROP POLICY IF EXISTS service_role_all ON {table_name};"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS esdata_all ON {table_name};"))
        op.execute(sa.text(f"ALTER TABLE IF EXISTS {table_name} DISABLE ROW LEVEL SECURITY;"))
