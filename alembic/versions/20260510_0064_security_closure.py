"""close residual RLS and function execute gaps

Revision ID: 20260510_0064_security_closure
Revises: 20260509_0063_articulo_timestamps
Create Date: 2026-05-10

The post-audit live database check found three public tables still outside
the zero-public-policy RLS baseline, plus two trigger functions with implicit
PUBLIC execute via null proacl. This migration aligns those late-created
objects with the S-TIER baseline.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260510_0064_security_closure"
down_revision = "20260509_0063_articulo_timestamps"
branch_labels = None
depends_on = None


TABLES = (
    "data_freshness_alerts",
    "dgt_queue",
    "source_freshness_snapshot",
)

FUNCTIONS = (
    "query_audit_log_append_only",
    "set_updated_at",
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

    for function_name in FUNCTIONS:
        op.execute(sa.text(f"REVOKE ALL ON FUNCTION {function_name}() FROM PUBLIC;"))
        op.execute(sa.text(f"GRANT EXECUTE ON FUNCTION {function_name}() TO esdata;"))
        op.execute(sa.text(f"GRANT EXECUTE ON FUNCTION {function_name}() TO service_role;"))


def downgrade() -> None:
    for function_name in FUNCTIONS:
        op.execute(sa.text(f"REVOKE EXECUTE ON FUNCTION {function_name}() FROM service_role;"))
        op.execute(sa.text(f"REVOKE EXECUTE ON FUNCTION {function_name}() FROM esdata;"))
        op.execute(sa.text(f"GRANT EXECUTE ON FUNCTION {function_name}() TO PUBLIC;"))

    bind = op.get_bind()
    for table_name in TABLES:
        exists = bind.execute(sa.text("SELECT to_regclass(:table_name)"), {"table_name": table_name}).scalar()
        if not exists:
            continue
        op.execute(sa.text(f"DROP POLICY IF EXISTS service_role_all ON {table_name};"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS esdata_all ON {table_name};"))
        op.execute(sa.text(f"ALTER TABLE IF EXISTS {table_name} DISABLE ROW LEVEL SECURITY;"))
