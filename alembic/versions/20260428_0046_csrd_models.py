"""Add CSRD (Corporate Sustainability Reporting Directive) data model tables.

Creates:
- csrd_entity_report: sustainability report for an entity
- csrd_esg_data_point: individual ESG data point
- csrd_ess: European Sustainability Reporting Standards catalog
- csrd_double_materiality: double materiality assessment

Revision ID: 20260428_0046_csrd_models
Revises: 20260428_0045_sfdr_models
Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0046_csrd_models"
down_revision = "20260428_0045_sfdr_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- csrd_entity_report: CSRD sustainability reports ---
    op.create_table(
        "csrd_entity_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=False),
        sa.Column("esap_url", sa.Text(), nullable=True),
        sa.Column("assurance_status", sa.Text(), nullable=True, server_default=sa.text("'none'::text")),
        sa.Column("reporting_standard", sa.Text(), nullable=True, server_default=sa.text("'ESGAS'::text")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'draft'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_csrd_er_entity", "entity_id"),
        sa.Index("ix_csrd_er_year", "reporting_year"),
        sa.Index("ix_csrd_er_status", "status"),
    )

    # --- csrd_esg_data_point: individual ESG data points ---
    op.create_table(
        "csrd_esg_data_point",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("indicator_code", sa.Text(), nullable=True),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("scope", sa.Integer(), nullable=True),
        sa.Column("verification_status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_csrd_edp_report", "report_id"),
        sa.Index("ix_csrd_edp_topic", "topic"),
    )

    # --- csrd_ess: European Sustainability Reporting Standards catalog ---
    op.create_table(
        "csrd_ess",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("standard_code", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=True),
        sa.Column("applicable_from_year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_csrd_ess_code", "standard_code"),
        sa.Index("ix_csrd_ess_topic", "topic"),
    )

    # --- csrd_double_materiality: double materiality assessment ---
    op.create_table(
        "csrd_double_materiality",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("impact_materiality", sa.JSON(), nullable=True),
        sa.Column("financial_materiality", sa.JSON(), nullable=True),
        sa.Column("assessment_date", sa.Date(), nullable=True),
        sa.Column("key_impacts", sa.Text(), nullable=True),
        sa.Column("key_dependencies", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'draft'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_csrd_dm_entity", "entity_id"),
        sa.Index("ix_csrd_dm_year", "assessment_date"),
    )


def downgrade():
    op.drop_table("csrd_double_materiality")
    op.drop_table("csrd_ess")
    op.drop_table("csrd_esg_data_point")
    op.drop_table("csrd_entity_report")
