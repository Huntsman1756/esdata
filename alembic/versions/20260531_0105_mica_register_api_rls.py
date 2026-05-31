"""grant API read access to MiCA register entries

Revision ID: 20260531_0105_mica_register_api_rls
Revises: 20260531_0104_mica_register_entries
Create Date: 2026-05-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260531_0105_mica_register_api_rls"
down_revision = "20260531_0104_mica_register_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'esdata_api') THEN
                    GRANT SELECT ON mica_register_entry TO esdata_api;

                    IF NOT EXISTS (
                        SELECT 1 FROM pg_policies
                        WHERE schemaname = 'public'
                          AND tablename = 'mica_register_entry'
                          AND policyname = 'esdata_api_select'
                    ) THEN
                        CREATE POLICY esdata_api_select ON mica_register_entry
                            FOR SELECT TO esdata_api
                            USING (true);
                    END IF;
                END IF;
            END
            $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS esdata_api_select ON mica_register_entry"))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'esdata_api') THEN
                    REVOKE SELECT ON mica_register_entry FROM esdata_api;
                END IF;
            END
            $$;
            """
        )
    )
