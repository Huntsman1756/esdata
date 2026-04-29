"""add pgc_xbrl_mapping table for IFRS/ESEF -> PGC account crosswalk

Creates pgc_xbrl_mapping table to store mappings between XBRL taxonomy
concepts (IFRS/ESEF) and PGC (Plan General Contable) chart of accounts.

# Revision ID: 20260426_0015_pgc_xbrl_mapping
# Revises: 20260426_0014_xbrl_taxonomy
# Create Date: 2026-04-26 00:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "20260426_0015_pgc_xbrl_mapping"
down_revision = "20260426_0014_xbrl_taxonomy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pgc_xbrl_mapping",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("xbrl_concept_qname", sa.Text(), nullable=False),
        sa.Column("pgc_account_codigo", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Text(), nullable=False, server_default=sa.text("'medium'::text")),
        sa.Column("mapping_type", sa.Text(), nullable=False, server_default=sa.text("'expert'::text")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "confidence IN ('high', 'medium', 'low')",
            name="chk_pgc_xbrl_mapping_confidence",
        ),
        sa.CheckConstraint(
            "mapping_type IN ('direct', 'similar', 'derived', 'expert')",
            name="chk_pgc_xbrl_mapping_type",
        ),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_xbrl_mapping_xbrl_concept
            ON pgc_xbrl_mapping(xbrl_concept_qname)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_xbrl_mapping_pgc_account
            ON pgc_xbrl_mapping(pgc_account_codigo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_xbrl_mapping_confidence
            ON pgc_xbrl_mapping(confidence)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pgc_xbrl_mapping_active
            ON pgc_xbrl_mapping(is_active)
            WHERE is_active = true
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uix_pgc_xbrl_mapping
            ON pgc_xbrl_mapping(xbrl_concept_qname, pgc_account_codigo)
        """
    )


def downgrade() -> None:
    op.drop_table("pgc_xbrl_mapping")
