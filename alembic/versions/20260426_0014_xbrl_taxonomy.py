"""add xbrl_taxonomy table for ESEF/IFRS taxonomy metadata

Creates xbrl_taxonomy table to store ESEF core, IFRS labels and metadata
for accounting concepts referenced by XBRL facts.

# Revision ID: 20260426_0014_xbrl_taxonomy
# Revises: 20260426_0013_xbrl
# Create Date: 2026-04-26 00:00:00

"""

from alembic import op


revision = "20260426_0014_xbrl_taxonomy"
down_revision = "20260426_0013_xbrl"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS xbrl_taxonomy (
            id SERIAL PRIMARY KEY,
            concept_qname TEXT NOT NULL,
            namespace TEXT NOT NULL,
            label TEXT NOT NULL,
            label_language TEXT NOT NULL DEFAULT 'en',
            label_role TEXT NOT NULL DEFAULT 'label',
            standard TEXT,
            data_type TEXT NOT NULL DEFAULT 'xbrli:monetaryItemType',
            period_type TEXT NOT NULL DEFAULT 'duration',
            is_monetary BOOLEAN NOT NULL DEFAULT TRUE,
            is_negative_allowed BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (concept_qname, label_language, label_role)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_taxonomy_concept_qname
            ON xbrl_taxonomy(concept_qname)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_taxonomy_namespace
            ON xbrl_taxonomy(namespace)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_taxonomy_standard
            ON xbrl_taxonomy(standard)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_taxonomy_language
            ON xbrl_taxonomy(label_language)
        """
    )


def downgrade() -> None:
    op.drop_table("xbrl_taxonomy")
