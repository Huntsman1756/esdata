"""Add Consumer Credit data model tables.

Creates:
- consumer_credit_contract: consumer credit contracts
- consumer_credit_disclosure: pre-contractual disclosure documents
- consumer_credit_overindebtedness: overindebtedness records

# Revision ID: 20260428_0050_consumer_credit_models
# Revises: 20260428_0049_psd2_sepa_models
# Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0050_consumer_credit_models"
down_revision = "20260428_0049_psd2_sepa_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- consumer_credit_contract: consumer credit contracts ---
    op.create_table(
        "consumer_credit_contract",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lender_id", sa.Integer(), nullable=True),
        sa.Column("borrower_id", sa.Integer(), nullable=True),
        sa.Column("credit_type", sa.Text(), nullable=False, server_default=sa.text("'installment'::text")),
        sa.Column("principal_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("annual_percentage_rate", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("term_months", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("signing_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_consumer_credit_contract_lender", "lender_id"),
    )

    # --- consumer_credit_disclosure: pre-contractual disclosure ---
    op.create_table(
        "consumer_credit_disclosure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("fap", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("total_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("regular_payment", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("amortization_schedule_url", sa.Text(), nullable=True),
        sa.Column("right_of_withdrawal", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("early_repayment_penalty", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_consumer_credit_disclosure_contract", "contract_id"),
    )

    # --- consumer_credit_overindebtedness: overindebtedness records ---
    op.create_table(
        "consumer_credit_overindebtedness",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("borrower_id", sa.Integer(), nullable=True),
        sa.Column("declared_date", sa.Date(), nullable=True),
        sa.Column("total_debt", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("monthly_income", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("unsecured_debt", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("procedure_status", sa.Text(), nullable=False, server_default=sa.text("'declared'::text")),
        sa.Column("court_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_consumer_credit_overindebtedness_borrower", "borrower_id"),
    )


def downgrade():
    op.drop_table("consumer_credit_overindebtedness")
    op.drop_table("consumer_credit_disclosure")
    op.drop_table("consumer_credit_contract")
