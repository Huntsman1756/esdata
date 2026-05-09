"""enable RLS on modelo_recurso (A-06)

Revision ID: 20260509_0062_rls_modelo_recurso
Revises: 20260509_0061_audit_append_only
Create Date: 2026-05-09

modelo_recurso is the largest populated table (9,659 rows) and was the only
one missing RLS per the zero-tolerance audit. This migration brings it in
line with the rest of the schema (159/163 tables already had RLS).

Policy shape mirrors the project default (esdata_all / service_role_all with
USING(true) WITH CHECK(true)). The trigger-based append-only enforcement in
query_audit_log is tighter and intentionally not applied here — modelo_recurso
is a materialised scrape of AEAT resource URLs which must be refreshable.
"""
from alembic import op

revision = "20260509_0062_rls_modelo_recurso"
down_revision = "20260509_0061_audit_append_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE modelo_recurso ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS esdata_all ON modelo_recurso;
        CREATE POLICY esdata_all ON modelo_recurso
            TO esdata
            USING (true)
            WITH CHECK (true);
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS service_role_all ON modelo_recurso;
        CREATE POLICY service_role_all ON modelo_recurso
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS service_role_all ON modelo_recurso;")
    op.execute("DROP POLICY IF EXISTS esdata_all ON modelo_recurso;")
    op.execute("ALTER TABLE modelo_recurso DISABLE ROW LEVEL SECURITY;")
