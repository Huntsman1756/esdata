"""Add CRD V/CRR, BRRD and EMIR data model tables.

Creates:
- crd_capital_position: capital position for CRD/CRR reporting
- crd_stress_test: stress test results
- brrd_bail_in: bail-in / MREL data
- emir_trade_report: trade reporting under EMIR
- emir_clearing_member: clearing member registration

Revision ID: 20260428_0048_crd_brrd_emir_models
Revises: 20260428_0047_aifmd_ucits_models
Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0048_crd_brrd_emir_models"
down_revision = "20260428_0047_aifmd_ucits_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- crd_capital_position: CRD/CRR capital position ---
    op.create_table(
        "crd_capital_position",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("reporting_date", sa.Date(), nullable=False),
        sa.Column("cet1_ratio", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("tier1_ratio", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("total_capital_ratio", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("cet1_amount", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("tier1_amount", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("total_capital_amount", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("leverage_ratio", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("risk_weighted_assets", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'filed'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_crd_cp_entity", "entity_id"),
        sa.Index("ix_crd_cp_date", "reporting_date"),
    )

    # --- crd_stress_test: CRD stress test results ---
    op.create_table(
        "crd_stress_test",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("test_date", sa.Date(), nullable=False),
        sa.Column("scenario_name", sa.Text(), nullable=True),
        sa.Column("cet1_impact_pct", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("tier1_impact_pct", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("capital_ratio_post_test", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("competent_authority", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'published'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_crd_st_entity", "entity_id"),
        sa.Index("ix_crd_st_date", "test_date"),
    )

    # --- brrd_bail_in: BRRD bail-in / MREL ---
    op.create_table(
        "brrd_bail_in",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("total_eligible_liabilities", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("mrel_target_pct", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("mrel_compliance_pct", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("internal_mrel", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("resolution_status", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_brrd_bi_entity", "entity_id"),
    )

    # --- emir_trade_report: EMIR trade reporting ---
    op.create_table(
        "emir_trade_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trade_id", sa.Text(), nullable=False),
        sa.Column("asset_class", sa.Text(), nullable=False, server_default=sa.text("'equity'::text")),
        sa.Column("instrument_class", sa.Text(), nullable=True),
        sa.Column("clearing_obligation_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reporting_delay_days", sa.Integer(), nullable=True),
        sa.Column("counterparty_type", sa.Text(), nullable=True, server_default=sa.text("'financial'::text")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'reported'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_emir_tr_trade_id", "trade_id"),
        sa.Index("ix_emir_tr_asset_class", "asset_class"),
    )

    # --- emir_clearing_member: EMIR clearing member ---
    op.create_table(
        "emir_clearing_member",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("emir_registration", sa.Text(), nullable=True),
        sa.Column("clearing_type", sa.Text(), nullable=False, server_default=sa.text("'central'::text")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_emir_cm_entity", "entity_id"),
        sa.Index("ix_emir_cm_type", "clearing_type"),
    )


def downgrade():
    op.drop_table("emir_clearing_member")
    op.drop_table("emir_trade_report")
    op.drop_table("brrd_bail_in")
    op.drop_table("crd_stress_test")
    op.drop_table("crd_capital_position")
