"""add CNMV consolidated version audit metadata

Revision ID: 20260514_0078_cnmv_consolidated_version_audit
Revises: 20260514_0077_aeat_instruction_key_tables
Create Date: 2026-05-14
"""

from alembic import op


revision = "20260514_0078_cnmv_consolidated_version_audit"
down_revision = "20260514_0077_aeat_instruction_key_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("documento_version", "documento_cnmv_version"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS es_consolidado BOOLEAN")
        op.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS consolidated_verification_status TEXT
            """
        )
        op.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS consolidated_source_url TEXT
            """
        )
        op.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS consolidated_checked_at TIMESTAMP WITH TIME ZONE
            """
        )
        op.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS boe_last_modified DATE
            """
        )
        op.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS consolidated_evidence_note TEXT
            """
        )
        op.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{table}_consolidated_status
            ON {table} (consolidated_verification_status)
            """
        )
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'ck_{table}_consolidated_status'
                ) THEN
                    ALTER TABLE {table}
                    ADD CONSTRAINT ck_{table}_consolidated_status
                    CHECK (
                        consolidated_verification_status IS NULL
                        OR consolidated_verification_status IN (
                            'consolidated',
                            'not_consolidated',
                            'unknown',
                            'verification_error'
                        )
                    );
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    for table in ("documento_cnmv_version", "documento_version"):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS ck_{table}_consolidated_status")
        op.execute(f"DROP INDEX IF EXISTS idx_{table}_consolidated_status")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS consolidated_evidence_note")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS boe_last_modified")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS consolidated_checked_at")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS consolidated_source_url")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS consolidated_verification_status")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS es_consolidado")
