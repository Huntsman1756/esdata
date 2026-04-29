"""add operability contract fields to sync_log

# Revision ID: 20260427_0031_sync_log_operability_contract
# Revises: 20260426_0030_ai_governance_persistence
# Create Date: 2026-04-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260427_0031_sync_log_operability_contract"
down_revision = "20260426_0030_ai_governance_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""ALTER TABLE sync_log ADD COLUMN IF NOT EXISTS rows_processed INTEGER""")
    op.execute("""ALTER TABLE sync_log ADD COLUMN IF NOT EXISTS errors INTEGER DEFAULT 0""")
    op.execute("""ALTER TABLE sync_log ADD COLUMN IF NOT EXISTS duration_ms INTEGER""")

    op.execute(
        """
        UPDATE sync_log
        SET rows_processed = COALESCE(rows_processed, bloques_processed, articulos_upserted, documentos_processed, documentos_upserted, 0)
        WHERE rows_processed IS NULL
        """
    )
    op.execute(
        """
        UPDATE sync_log
        SET errors = COALESCE(errors, CASE WHEN error_msg IS NULL OR error_msg = '' THEN 0 ELSE 1 END)
        WHERE errors IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("sync_log", "duration_ms")
    op.drop_column("sync_log", "errors")
    op.drop_column("sync_log", "rows_processed")
