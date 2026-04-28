"""Add IDD and Solvency II data model tables.

Creates:
- idd_distributor: insurance distribution distributors
- idd_product_uci: UCI product documents
- solvency_ii_entity: Solvency II reporting entities
- solvency_ii_sfp: summary of fund portfolio

Revision ID: 20260428_0051_idd_solvency_models
Revises: 20260428_0050_consumer_credit_models
Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0051_idd_solvency_models"
down_revision = "20260428_0050_consumer_credit_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- idd_distributor: insurance distribution distributors ---
    op.create_table(
        "idd_distributor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("insurance_ao", sa.Text(), nullable=True),
        sa.Column("products_covered", sa.Text(), nullable=True),
        sa.Column("professional_indemnity", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("training_certified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_idd_distributor_entity", "entity_id"),
    )

    # --- idd_product_uci: UCI product documents ---
    op.create_table(
        "idd_product_uci",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_type", sa.Text(), nullable=False, server_default=sa.text("'life'::text")),
        sa.Column("risk_coverage", sa.Text(), nullable=True),
        sa.Column("cost_breakdown", sa.Text(), nullable=True),
        sa.Column("exit_costs", sa.Text(), nullable=True),
        sa.Column("taxes", sa.Text(), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_idd_product_uci_product", "product_id"),
    )

    # --- solvency_ii_entity: Solvency II reporting entities ---
    op.create_table(
        "solvency_ii_entity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.Text(), nullable=False, server_default=sa.text("'life'::text")),
        sa.Column("solvency_capital_requirement", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("minimum_capital_requirement", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("solvency_ratio", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("reporting_date", sa.Date(), nullable=True),
        sa.Column("home_supervisor", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_solvency_ii_entity_entity", "entity_id"),
    )

    # --- solvency_ii_sfp: summary of fund portfolio ---
    op.create_table(
        "solvency_ii_sfp",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("reporting_period", sa.Text(), nullable=True),
        sa.Column("fund_breakdown", sa.Text(), nullable=True),
        sa.Column("asset_allocation", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'published'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_solvency_ii_sfp_entity", "entity_id"),
    )


def downgrade():
    op.drop_table("solvency_ii_sfp")
    op.drop_table("solvency_ii_entity")
    op.drop_table("idd_product_uci")
    op.drop_table("idd_distributor")
