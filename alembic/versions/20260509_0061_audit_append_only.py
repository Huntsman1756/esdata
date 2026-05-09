"""query_audit_log append-only trigger + merge heads

Revision ID: 20260509_0061_audit_append_only
Revises: ('20260429_0052_merge_0037_heads', '20260508_0059_cdi_enrichment', '20260509_0060_dead_letter')
Create Date: 2026-05-09

Enforces append-only semantics on query_audit_log at the database level:
a BEFORE UPDATE/DELETE trigger raises an exception for any non-INSERT write.
This fixes the S-17 gap where application-level role (esdata=superuser) could
otherwise mutate audit entries, bypassing the RLS policies that currently use
USING(true) WITH CHECK(true).

Also serves as a merge migration for the three outstanding heads so that
`alembic upgrade heads` converges on a single head going forward.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260509_0061_audit_append_only'
down_revision = (
    '20260429_0052_merge_0037_heads',
    '20260508_0059_cdi_enrichment',
    '20260509_0060_dead_letter',
)
branch_labels = None
depends_on = None


TRIGGER_FN_SQL = """
CREATE OR REPLACE FUNCTION query_audit_log_append_only()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION
            'query_audit_log is append-only: UPDATE not permitted (row id=%)',
            OLD.id
            USING ERRCODE = 'insufficient_privilege';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'query_audit_log is append-only: DELETE not permitted (row id=%)',
            OLD.id
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    # Install the guard function.
    op.execute(TRIGGER_FN_SQL)

    # Attach trigger for UPDATE and DELETE. Use the same function for both
    # operations; the function inspects TG_OP to emit the appropriate message.
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_query_audit_log_no_update ON query_audit_log;
        CREATE TRIGGER trg_query_audit_log_no_update
        BEFORE UPDATE ON query_audit_log
        FOR EACH ROW
        EXECUTE FUNCTION query_audit_log_append_only();
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_query_audit_log_no_delete ON query_audit_log;
        CREATE TRIGGER trg_query_audit_log_no_delete
        BEFORE DELETE ON query_audit_log
        FOR EACH ROW
        EXECUTE FUNCTION query_audit_log_append_only();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_query_audit_log_no_delete ON query_audit_log;")
    op.execute("DROP TRIGGER IF EXISTS trg_query_audit_log_no_update ON query_audit_log;")
    op.execute("DROP FUNCTION IF EXISTS query_audit_log_append_only();")
