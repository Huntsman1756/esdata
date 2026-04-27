"""add xbrl filing and fact tables

Creates xbrl_filing and xbrl_fact tables for the fixture-first
XBRL slice, keeping schema parity with the validated test contract.

Revision ID: 20260426_0013_xbrl
Revises: 20260426_0012_screening
Create Date: 2026-04-26 00:00:00

"""

from alembic import op


revision = "20260426_0013_xbrl"
down_revision = "20260426_0012_screening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # xbrl_filing: normalized filing metadata for a parsed XBRL source
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS xbrl_filing (
            id SERIAL PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_path TEXT NOT NULL UNIQUE,
            entity_identifier TEXT NOT NULL,
            period_start DATE,
            period_end DATE,
            filing_type TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_filing_entity_identifier
            ON xbrl_filing(entity_identifier)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_filing_period_end
            ON xbrl_filing(period_end)
        """
    )

    # xbrl_fact: persisted facts linked to the normalized filing row
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS xbrl_fact (
            id SERIAL PRIMARY KEY,
            filing_id INTEGER NOT NULL REFERENCES xbrl_filing(id),
            concept TEXT NOT NULL,
            value_raw TEXT NOT NULL,
            value_numeric NUMERIC(18,2),
            unit TEXT,
            context_ref TEXT,
            period_start DATE,
            period_end DATE,
            entity_identifier TEXT NOT NULL,
            decimals TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (filing_id, concept, context_ref, value_raw)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_fact_filing
            ON xbrl_fact(filing_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_fact_entity_identifier
            ON xbrl_fact(entity_identifier)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_fact_concept
            ON xbrl_fact(concept)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_xbrl_fact_period_end
            ON xbrl_fact(period_end)
        """
    )


def downgrade() -> None:
    op.drop_table("xbrl_fact")
    op.drop_table("xbrl_filing")
