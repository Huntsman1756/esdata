"""add response payload to query_audit_log

# Revision ID: 20260503_0055_query_audit_response_payload
# Revises: 20260501_0054_aeat_modelo_recurso
# Create Date: 2026-05-03 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260503_0055_query_audit_response_payload"
down_revision = "20260501_0054_aeat_modelo_recurso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS tool_name TEXT NOT NULL DEFAULT ''"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS sources TEXT NOT NULL DEFAULT '[]'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS confidence TEXT NOT NULL DEFAULT '{}'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS completeness TEXT NOT NULL DEFAULT 'parcial'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS verified INTEGER NOT NULL DEFAULT 0"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS response_payload TEXT NOT NULL DEFAULT '{}'"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS response_payload"))
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS verified"))
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS completeness"))
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS confidence"))
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS sources"))
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS tool_name"))
