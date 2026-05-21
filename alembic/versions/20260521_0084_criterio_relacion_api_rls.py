"""grant runtime api read access to criterio relacion

Revision ID: 20260521_0084_criterio_relacion_api_rls
Revises: 20260521_0083_doctrina_criterio_relacion
Create Date: 2026-05-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260521_0084_criterio_relacion_api_rls"
down_revision = "20260521_0083_doctrina_criterio_relacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'esdata_api') THEN
                    GRANT SELECT ON criterio_relacion TO esdata_api;

                    IF NOT EXISTS (
                        SELECT 1 FROM pg_policies
                        WHERE schemaname = 'public'
                          AND tablename = 'criterio_relacion'
                          AND policyname = 'esdata_api_select'
                    ) THEN
                        CREATE POLICY esdata_api_select ON criterio_relacion
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
    op.execute(sa.text("DROP POLICY IF EXISTS esdata_api_select ON criterio_relacion"))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'esdata_api') THEN
                    REVOKE SELECT ON criterio_relacion FROM esdata_api;
                END IF;
            END
            $$;
            """
        )
    )
