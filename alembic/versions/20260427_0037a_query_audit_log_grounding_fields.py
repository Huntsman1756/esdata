"""add grounding fields to query_audit_log

# Revision ID: 20260427_0037a_query_audit_log_grounding_fields
# Revises: 20260427_0036_mica_crypto_models
# Create Date: 2026-04-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260427_0037a_query_audit_log_grounding_fields"
down_revision = "20260427_0036_mica_crypto_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS grounding_status TEXT DEFAULT ''"))
    op.execute(
        sa.text(
            "ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS prompt_injection_detected INTEGER NOT NULL DEFAULT 0"
        )
    )
    op.execute(sa.text("ALTER TABLE query_audit_log ADD COLUMN IF NOT EXISTS grounding_summary TEXT NOT NULL DEFAULT '{}'"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS grounding_summary"))
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS prompt_injection_detected"))
    op.execute(sa.text("ALTER TABLE query_audit_log DROP COLUMN IF EXISTS grounding_status"))
