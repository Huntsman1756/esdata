"""add SFDR (Sustainable Finance Disclosure Regulation) data model tables.

Creates:
- sfdr_product: investment product with sustainability strategy
- sfdr_paci_indicator: PCAI indicator values
- sfdr_entity_paci: entity-level PCAI (Art. 4)
- sfdr_pre_contractual: pre-contractual SFDR documents
- sfdr_annual_report: annual SFDR reports

Revision ID: 20260428_0045_sfdr_models
Revises: 20260428_0044_transparency_models
Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0045_sfdr_models"
down_revision = "20260428_0044_transparency_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- sfdr_product: SFDR investment products (Art. 6, 8, 9) ---
    op.create_table(
        "sfdr_product",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("product_type", sa.Text(), nullable=False, server_default=sa.text("'other'::text")),
        sa.Column("sustainability_strategy", sa.Text(), nullable=True),
        sa.Column("principal_adverse_impact", sa.Text(), nullable=True, server_default=sa.text("'false'::text")),
        sa.Column("paci_aggregated", sa.JSON(), nullable=True),
        sa.Column("paci_detailed_url", sa.Text(), nullable=True),
        sa.Column("distribution_country", sa.JSON(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_sfdr_product_type", "product_type"),
        sa.Index("ix_sfdr_product_status", "status"),
        sa.Index("ix_sfdr_product_name", "product_name"),
    )

    # --- sfdr_paci_indicator: PCAI indicator values ---
    op.create_table(
        "sfdr_paci_indicator",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("indicator_code", sa.Text(), nullable=False),
        sa.Column("indicator_name", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("reference_period", sa.Text(), nullable=True),
        sa.Column("methodology", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_sfdr_paci_product", "product_id"),
        sa.Index("ix_sfdr_paci_code", "indicator_code"),
        sa.Index("ix_sfdr_paci_status", "status"),
    )

    # --- sfdr_entity_paci: entity-level PCAI (SFDR Art. 4) ---
    op.create_table(
        "sfdr_entity_paci",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=False),
        sa.Column("aggregated_paci", sa.JSON(), nullable=True),
        sa.Column("sectoral_decarbonization", sa.JSON(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'draft'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_sfdr_epaci_entity", "entity_id"),
        sa.Index("ix_sfdr_epaci_year", "reporting_year"),
        sa.Index("ix_sfdr_epaci_status", "status"),
    )

    # --- sfdr_pre_contractual: pre-contractual SFDR documents ---
    op.create_table(
        "sfdr_pre_contractual",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_sfdr_pc_product", "product_id"),
        sa.Index("ix_sfdr_pc_type", "document_type"),
        sa.Index("ix_sfdr_pc_status", "status"),
    )

    # --- sfdr_annual_report: annual SFDR reports ---
    op.create_table(
        "sfdr_annual_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=False),
        sa.Column("paci_results", sa.JSON(), nullable=True),
        sa.Column("engagement_activities", sa.JSON(), nullable=True),
        sa.Column("good_practice_examples", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'draft'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_sfdr_ar_entity", "entity_id"),
        sa.Index("ix_sfdr_ar_year", "reporting_year"),
        sa.Index("ix_sfdr_ar_status", "status"),
    )


def downgrade():
    op.drop_table("sfdr_annual_report")
    op.drop_table("sfdr_pre_contractual")
    op.drop_table("sfdr_entity_paci")
    op.drop_table("sfdr_paci_indicator")
    op.drop_table("sfdr_product")
