"""add Ley 11/2021 (antifraude) data model tables.

Creates:
- fraud_prevention_program: anti-fraud prevention programs
- fraud_risk_assessment: fraud risk assessments
- fraud_incident: fraud incident records

Revision ID: 20260427_0039_ley11_2021_models
Revises: 20260427_0038_ley10_2010_models
Create Date: 2026-04-27 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260427_0039_ley11_2021_models"
down_revision = "20260427_0038_ley10_2010_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- fraud_prevention_program: anti-fraud programs ---
    op.create_table(
        "fraud_prevention_program",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("code_of_conduct", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("internal_reporting_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("training_schedule", sa.Text(), nullable=True),
        sa.Column("audit_frequency", sa.Text(), nullable=True),
        sa.Column("compliance_officer_name", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_fraud_prevention_program_entity", "entity_id"),
    )

    # --- fraud_risk_assessment: risk assessments ---
    op.create_table(
        "fraud_risk_assessment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("assessment_date", sa.Date(), nullable=True),
        sa.Column("risk_areas", sa.Text(), nullable=True),
        sa.Column("mitigation_measures", sa.Text(), nullable=True),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_fraud_risk_assessment_entity", "entity_id"),
    )

    # --- fraud_incident: fraud incidents ---
    op.create_table(
        "fraud_incident",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("incident_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount_eur", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'open'::text")),
        sa.Column("resolution_date", sa.Date(), nullable=True),
        sa.Column("regulatory_notification", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_fraud_incident_entity", "entity_id"),
        sa.Index("ix_fraud_incident_status", "status"),
    )


def downgrade():
    op.drop_table("fraud_incident")
    op.drop_table("fraud_risk_assessment")
    op.drop_table("fraud_prevention_program")
