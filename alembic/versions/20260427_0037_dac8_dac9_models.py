"""add DAC8/DAC9 crypto-asset information exchange tables.

Creates:
- dac_reporting_entity: reporting entities obligated to submit DAC8/DAC9 reports
- dac_crypto_report: periodic crypto transaction reports
- dac_wallet_holder: wallet holders within a report

# Revision ID: 20260427_0037_dac8_dac9_models
# Revises: 20260427_0036_mica_crypto_models
# Create Date: 2026-04-27 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260427_0037_dac8_dac9_models"
down_revision = "20260427_0036_mica_crypto_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- dac_reporting_entity: reporting entities obligated to submit DAC8/DAC9 reports ---
    op.create_table(
        "dac_reporting_entity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tin", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.Text(), nullable=True),
        sa.Column("member_state", sa.Text(), nullable=True),
        sa.Column("dac8_registered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dac9_registered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_dac_reporting_entity_tin", "tin"),
        sa.Index("ix_dac_reporting_entity_state", "member_state"),
        sa.Index("ix_dac_reporting_entity_type", "entity_type"),
        sa.Index("ix_dac_reporting_entity_status", "status"),
    )

    # --- dac_crypto_report: periodic crypto transaction report ---
    op.create_table(
        "dac_crypto_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("reporting_period", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'draft'::text")),
        sa.Column("crypto_transactions_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("wallet_holders_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_dac_crypto_report_entity", "entity_id"),
        sa.Index("ix_dac_crypto_report_period", "reporting_period"),
        sa.Index("ix_dac_crypto_report_status", "status"),
    )

    # --- dac_wallet_holder: wallet holders within a report ---
    op.create_table(
        "dac_wallet_holder",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column("wallet_address", sa.Text(), nullable=True),
        sa.Column("holder_tin", sa.Text(), nullable=True),
        sa.Column("holder_member_state", sa.Text(), nullable=True),
        sa.Column("holder_type", sa.Text(), nullable=True),
        sa.Column("total_value_eur", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("verification_status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_dac_wallet_holder_report", "report_id"),
        sa.Index("ix_dac_wallet_holder_address", "wallet_address"),
        sa.Index("ix_dac_wallet_holder_state", "holder_member_state"),
        sa.Index("ix_dac_wallet_holder_status", "verification_status"),
    )


def downgrade():
    op.drop_table("dac_wallet_holder")
    op.drop_table("dac_crypto_report")
    op.drop_table("dac_reporting_entity")
