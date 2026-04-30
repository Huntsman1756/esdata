"""Add Onda 2 missing tables.

Creates:
- crd_brrd_emir_entity: CRD V / BRRD / EMIR entities
- sfdr_fund: SFDR funds
- csrd_company: CSRD reporting companies
- pbc_entity: PBC (prudential buffer capital) entities
- xbrl_company: XBRL filers

# Revision ID: 20260430_0052_onda2_missing_tables
# Revises: 20260428_0051_idd_solvency_models
# Create Date: 2026-04-30 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260430_0052_onda2_missing_tables"
down_revision = "20260428_0051_idd_solvency_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- crd_brrd_emir_entity ---
    op.create_table(
        "crd_brrd_emir_entity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("entity_name", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("capital_ratio_tier1", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("capital_ratio_cet1", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_crd_brrd_emir_entity_entity", "entity_id"),
    )

    # --- sfdr_fund ---
    op.create_table(
        "sfdr_fund",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), nullable=True),
        sa.Column("fund_name", sa.Text(), nullable=False),
        sa.Column("fund_type", sa.Text(), nullable=False),
        sa.Column("sfdr_article", sa.Text(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_sfdr_fund_fund", "fund_id"),
    )

    # --- csrd_company ---
    op.create_table(
        "csrd_company",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("company_type", sa.Text(), nullable=False),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_csrd_company_company", "company_id"),
    )

    # --- pbc_entity ---
    op.create_table(
        "pbc_entity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("entity_name", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("pbc_ratio", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("capital_ratio_tier1", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_pbc_entity_entity", "entity_id"),
    )

    # --- xbrl_company ---
    op.create_table(
        "xbrl_company",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("company_type", sa.Text(), nullable=False),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_xbrl_company_company", "company_id"),
    )


def downgrade():
    op.drop_table("xbrl_company")
    op.drop_table("pbc_entity")
    op.drop_table("csrd_company")
    op.drop_table("sfdr_fund")
    op.drop_table("crd_brrd_emir_entity")
