"""Add AIFMD and UCITS data model tables.

Creates:
- aifmd_fund: Alternative Investment Fund
- ucits_fund: UCITS fund
- aifmd_regulatory_report: regulatory reports for AIFMD funds
- ucits_regulatory_report: regulatory reports for UCITS funds
- aifmd_liquidity_management: liquidity management data

# Revision ID: 20260428_0047_aifmd_ucits_models
# Revises: 20260428_0046_csrd_models
# Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0047_aifmd_ucits_models"
down_revision = "20260428_0046_csrd_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- aifmd_fund: Alternative Investment Fund ---
    op.create_table(
        "aifmd_fund",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_name", sa.Text(), nullable=False),
        sa.Column("aifm_id", sa.Integer(), nullable=True),
        sa.Column("fund_type", sa.Text(), nullable=False, server_default=sa.text("'alternative'::text")),
        sa.Column("registration_date", sa.Date(), nullable=True),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("cross_border_passport", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("total_aum_eur", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("investor_type", sa.Text(), nullable=True, server_default=sa.text("'professional'::text")),
        sa.Column("lock_up_period", sa.Text(), nullable=True),
        sa.Column("redemption_frequency", sa.Text(), nullable=True),
        sa.Column("leverage_method", sa.Text(), nullable=True),
        sa.Column("leverage_max_pct", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_aifmd_fund_name", "fund_name"),
        sa.Index("ix_aifmd_fund_type", "fund_type"),
        sa.Index("ix_aifmd_fund_status", "status"),
    )

    # --- ucits_fund: UCITS fund ---
    op.create_table(
        "ucits_fund",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_name", sa.Text(), nullable=False),
        sa.Column("management_company", sa.Text(), nullable=True),
        sa.Column("registration_date", sa.Date(), nullable=True),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("cross_border_passport", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("total_aum_eur", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("depositary_id", sa.Integer(), nullable=True),
        sa.Column("krid_url", sa.Text(), nullable=True),
        sa.Column("investment_strategy", sa.Text(), nullable=True),
        sa.Column("risk_profile", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_ucits_fund_name", "fund_name"),
        sa.Index("ix_ucits_fund_company", "management_company"),
        sa.Index("ix_ucits_fund_status", "status"),
    )

    # --- aifmd_regulatory_report: AIFMD regulatory reports ---
    op.create_table(
        "aifmd_regulatory_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.Text(), nullable=False, server_default=sa.text("'annual'::text")),
        sa.Column("reporting_period", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("filed_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'draft'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_aifmd_rr_fund", "fund_id"),
        sa.Index("ix_aifmd_rr_type", "report_type"),
    )

    # --- ucits_regulatory_report: UCITS regulatory reports ---
    op.create_table(
        "ucits_regulatory_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.Text(), nullable=False, server_default=sa.text("'annual'::text")),
        sa.Column("reporting_period", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("filed_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'draft'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_ucits_rr_fund", "fund_id"),
        sa.Index("ix_ucits_rr_type", "report_type"),
    )

    # --- aifmd_liquidity_management: Liquidity management ---
    op.create_table(
        "aifmd_liquidity_management",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("redemption_suspended", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("suspension_date", sa.Date(), nullable=True),
        sa.Column("gating_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("swing_price_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("side_pocket_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("stress_test_result", sa.Text(), nullable=True),
        sa.Column("valuation_frequency", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_aifmd_lm_fund", "fund_id"),
    )


def downgrade():
    op.drop_table("aifmd_liquidity_management")
    op.drop_table("ucits_regulatory_report")
    op.drop_table("aifmd_regulatory_report")
    op.drop_table("ucits_fund")
    op.drop_table("aifmd_fund")
