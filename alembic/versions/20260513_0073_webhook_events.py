"""migrate webhook idempotency table out of runtime DDL

Revision ID: 20260513_0073_webhook_events
Revises: 20260512_0072_documento_interpretativo_metadata
Create Date: 2026-05-13

`apps/api/services/webhook_verification.py` previously created webhook_events
at request time. This migration makes the table Alembic-owned and applies the
backend-only RLS baseline.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260513_0073_webhook_events"
down_revision = "20260512_0072_documento_interpretativo_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(sa.text("ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;"))
    op.execute(sa.text("DROP POLICY IF EXISTS esdata_all ON webhook_events;"))
    op.execute(
        sa.text(
            """
            CREATE POLICY esdata_all ON webhook_events
                TO esdata
                USING (true)
                WITH CHECK (true);
            """
        )
    )
    op.execute(sa.text("DROP POLICY IF EXISTS service_role_all ON webhook_events;"))
    op.execute(
        sa.text(
            """
            CREATE POLICY service_role_all ON webhook_events
                TO service_role
                USING (true)
                WITH CHECK (true);
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS service_role_all ON webhook_events;"))
    op.execute(sa.text("DROP POLICY IF EXISTS esdata_all ON webhook_events;"))
    op.execute(sa.text("ALTER TABLE IF EXISTS webhook_events DISABLE ROW LEVEL SECURITY;"))
    op.execute(sa.text("DROP TABLE IF EXISTS webhook_events;"))
