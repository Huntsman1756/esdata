"""add MiFID II/MiFIR data model tables.

Creates:
- mifid_client_category: client classification (retail/professional/counterparty)
- mifid_suitability_report: suitability and appropriateness assessments
- mifid_best_execution_record: best execution monitoring
- mifid_conflict_of_interest_registry: conflict identification and mitigation
- mifid_product_governance: target market and distribution governance
- mifid_order_record: order management and retention
- mifid_insider_list: insider list management (MAR Art. 18)
- mifid_compensation_policy: risk-aligned compensation

Revision ID: 20260428_0040_mifid_mir_models
Revises: 20260427_0039_ley11_2021_models
Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0040_mifid_mir_models"
down_revision = "20260427_0039_ley11_2021_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- mifid_client_category: MiFID II client classification ---
    op.create_table(
        "mifid_client_category",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("assessment_date", sa.Date(), nullable=True),
        sa.Column("knowledge_level", sa.Text(), nullable=True),
        sa.Column("experience_level", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mifid_client_category_entity", "entity_id"),
        sa.Index("ix_mifid_client_category_cat", "category"),
        sa.Index("ix_mifid_client_category_status", "status"),
    )

    # --- mifid_suitability_report: suitability assessments ---
    op.create_table(
        "mifid_suitability_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("assessment_date", sa.Date(), nullable=True),
        sa.Column("suitability_score", sa.Integer(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("advisor_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mifid_suitability_client", "client_id"),
        sa.Index("ix_mifid_suitability_date", "assessment_date"),
        sa.Index("ix_mifid_suitability_status", "status"),
    )

    # --- mifid_best_execution_record: best execution monitoring ---
    op.create_table(
        "mifid_best_execution_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("venue", sa.Text(), nullable=True),
        sa.Column("execution_price", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("market_impact", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("speed_ms", sa.Integer(), nullable=True),
        sa.Column("quality_metrics", sa.JSON(), nullable=True),
        sa.Column("execution_timestamp", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mifid_best_exec_venue", "venue"),
        sa.Index("ix_mifid_best_exec_ts", "execution_timestamp"),
        sa.Index("ix_mifid_best_exec_status", "status"),
    )

    # --- mifid_conflict_of_interest_registry: conflict management ---
    op.create_table(
        "mifid_conflict_of_interest_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department", sa.Text(), nullable=True),
        sa.Column("conflict_type", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mitigation_measure", sa.Text(), nullable=True),
        sa.Column("identified_date", sa.Date(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mifid_coi_type", "conflict_type"),
        sa.Index("ix_mifid_coi_status", "status"),
    )

    # --- mifid_product_governance: product governance ---
    op.create_table(
        "mifid_product_governance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("target_market", sa.Text(), nullable=True),
        sa.Column("distribution_channels", sa.JSON(), nullable=True),
        sa.Column("key_features", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.Integer(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mifid_pg_product", "product_id"),
        sa.Index("ix_mifid_pg_risk", "risk_level"),
        sa.Index("ix_mifid_pg_status", "status"),
    )

    # --- mifid_order_record: order management ---
    op.create_table(
        "mifid_order_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("instrument", sa.Text(), nullable=True),
        sa.Column("direction", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("price", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("venue", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("retention_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mifid_order_client", "client_id"),
        sa.Index("ix_mifid_order_instrument", "instrument"),
        sa.Index("ix_mifid_order_ts", "timestamp"),
        sa.Index("ix_mifid_order_status", "status"),
    )

    # --- mifid_insider_list: insider list management ---
    op.create_table(
        "mifid_insider_list",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("insider_name", sa.Text(), nullable=True),
        sa.Column("insider_tin", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("inside_information_description", sa.Text(), nullable=True),
        sa.Column("date_created", sa.Date(), nullable=True),
        sa.Column("date_removed", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mifid_insider_entity", "entity_id"),
        sa.Index("ix_mifid_insider_status", "status"),
    )

    # --- mifid_compensation_policy: risk-aligned compensation ---
    op.create_table(
        "mifid_compensation_policy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("policy_version", sa.Text(), nullable=True),
        sa.Column("alignment_score", sa.Integer(), nullable=True),
        sa.Column("risk_adjustment_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approval_date", sa.Date(), nullable=True),
        sa.Column("next_review", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mifid_comp_entity", "entity_id"),
        sa.Index("ix_mifid_comp_status", "status"),
    )


def downgrade():
    op.drop_table("mifid_compensation_policy")
    op.drop_table("mifid_insider_list")
    op.drop_table("mifid_order_record")
    op.drop_table("mifid_product_governance")
    op.drop_table("mifid_conflict_of_interest_registry")
    op.drop_table("mifid_best_execution_record")
    op.drop_table("mifid_suitability_report")
    op.drop_table("mifid_client_category")
