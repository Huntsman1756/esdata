"""close RLS gaps on monitoring and operational tables

Revision ID: 20260510_0067_monitoring_rls_closure
Revises: 20260510_0066_cdi_country_unique
Create Date: 2026-05-10

Production audit evidence showed late-created operational tables without the
S-TIER RLS baseline. These tables are backend-only and must be reachable only
by server roles.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260510_0067_monitoring_rls_closure"
down_revision = "20260510_0066_cdi_country_unique"
branch_labels = None
depends_on = None


TABLES = (
    "data_freshness_alerts",
    "source_freshness_snapshot",
    "sync_dead_letter",
)


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in TABLES:
        exists = bind.execute(sa.text("SELECT to_regclass(:table_name)"), {"table_name": table_name}).scalar()
        if not exists:
            continue

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


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in TABLES:
        exists = bind.execute(sa.text("SELECT to_regclass(:table_name)"), {"table_name": table_name}).scalar()
        if not exists:
            continue

        op.execute(sa.text(f"DROP POLICY IF EXISTS service_role_all ON {table_name};"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS esdata_all ON {table_name};"))
        op.execute(sa.text(f"ALTER TABLE IF EXISTS {table_name} DISABLE ROW LEVEL SECURITY;"))
