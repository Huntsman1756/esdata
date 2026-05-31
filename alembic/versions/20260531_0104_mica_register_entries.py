"""add traced ESMA MiCA register entries

Revision ID: 20260531_0104_mica_register_entries
Revises: 20260525_0103_aeat_172_173_current_docs_2025
Create Date: 2026-05-31

Stores ESMA MiCA interim register CSV rows that are not CASP rows. CASP keeps
its dedicated table; this table is for white papers, ART/EMT issuers and
non-compliant entities with row-level provenance.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260531_0104_mica_register_entries"
down_revision = "20260525_0103_aeat_172_173_current_docs_2025"
branch_labels = None
depends_on = None


def _enable_backend_rls(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
    for policy_name, role_name in (
        ("esdata_all", "esdata"),
        ("service_role_all", "service_role"),
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_name} ON {table_name};"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {policy_name} ON {table_name}
                    TO {role_name}
                    USING (true)
                    WITH CHECK (true);
                """
            )
        )


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS mica_register_entry (
                id SERIAL PRIMARY KEY,
                register_type VARCHAR(40) NOT NULL,
                register_label TEXT NOT NULL,
                source_row_id VARCHAR(128) NOT NULL,
                name TEXT,
                entity_identifier TEXT,
                home_member_state VARCHAR(20),
                status TEXT,
                raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                source_url TEXT NOT NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                verified BOOLEAN NOT NULL DEFAULT false,
                completeness VARCHAR(50) NOT NULL DEFAULT 'parcial',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(register_type, source_row_id)
            )
            """
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_mica_register_type ON mica_register_entry(register_type);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_mica_register_name ON mica_register_entry(name);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_mica_register_state ON mica_register_entry(home_member_state);"))
    _enable_backend_rls("mica_register_entry")


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS mica_register_entry"))
