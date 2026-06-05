"""add diagnostic details to sync_log

Revision ID: 20260605_0120_sync_log_diagnostic_details
Revises: 20260604_0119_firds_metadata_only
Create Date: 2026-06-05

Store bounded structured diagnostics for worker sync rows, such as failed
candidate URLs discovered during source ingestion.
"""

from __future__ import annotations

from alembic import op

revision = "20260605_0120_sync_log_diagnostic_details"
down_revision = "20260604_0119_firds_metadata_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE sync_log ADD COLUMN IF NOT EXISTS diagnostic_details JSONB")


def downgrade() -> None:
    op.drop_column("sync_log", "diagnostic_details")
