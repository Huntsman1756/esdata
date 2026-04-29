"""add DORA (Digital Operational Resilience Act) data model tables.

Creates:
- dora_tic_incident: ICT incident tracking and classification
- dora_third_party_provider: critical TPT management
- dora_ict_risk_register: ICT risk assessment register
- dora_penetration_test: penetration testing records
- dora_incident_classification_framework: severity classification framework

# Revision ID: 20260428_0042_dora_models
# Revises: 20260428_0041_mar_models
# Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0042_dora_models"
down_revision = "20260428_0041_mar_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- dora_tic_incident: ICT incident tracking ---
    op.create_table(
        "dora_tic_incident",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("incident_severity", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("impact_scope", sa.Text(), nullable=True),
        sa.Column("detection_date", sa.Date(), nullable=True),
        sa.Column("resolution_date", sa.Date(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("classification", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'open'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_dora_tic_severity", "incident_severity"),
        sa.Index("ix_dora_tic_class", "classification"),
        sa.Index("ix_dora_tic_status", "status"),
        sa.Index("ix_dora_tic_detection", "detection_date"),
    )

    # --- dora_third_party_provider: critical TPT management ---
    op.create_table(
        "dora_third_party_provider",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_name", sa.Text(), nullable=True),
        sa.Column("provider_type", sa.Text(), nullable=True),
        sa.Column("criticality_assessment", sa.Text(), nullable=True),
        sa.Column("contract_start", sa.Date(), nullable=True),
        sa.Column("contract_end", sa.Date(), nullable=True),
        sa.Column("eu_supervision_status", sa.Text(), nullable=True),
        sa.Column("exit_strategy", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_dora_tpp_type", "provider_type"),
        sa.Index("ix_dora_tpp_crit", "criticality_assessment"),
        sa.Index("ix_dora_tpp_status", "status"),
    )

    # --- dora_ict_risk_register: ICT risk register ---
    op.create_table(
        "dora_ict_risk_register",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("risk_description", sa.Text(), nullable=True),
        sa.Column("likelihood", sa.Text(), nullable=True),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_dora_ict_risk_entity", "entity_id"),
        sa.Index("ix_dora_ict_risk_likelihood", "likelihood"),
        sa.Index("ix_dora_ict_risk_status", "status"),
    )

    # --- dora_penetration_test: penetration testing records ---
    op.create_table(
        "dora_penetration_test",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("test_type", sa.Text(), nullable=True),
        sa.Column("tester", sa.Text(), nullable=True),
        sa.Column("test_date", sa.Date(), nullable=True),
        sa.Column("findings_count", sa.Integer(), nullable=True),
        sa.Column("critical_findings", sa.Integer(), nullable=True),
        sa.Column("remediation_deadline", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'scheduled'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_dora_pt_entity", "entity_id"),
        sa.Index("ix_dora_pt_type", "test_type"),
        sa.Index("ix_dora_pt_status", "status"),
    )

    # --- dora_incident_classification_framework: severity classification ---
    op.create_table(
        "dora_incident_classification_framework",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("framework_version", sa.Text(), nullable=True),
        sa.Column("severity_thresholds", sa.JSON(), nullable=True),
        sa.Column("reporting_timelines", sa.JSON(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_dora_icf_version", "framework_version"),
        sa.Index("ix_dora_icf_status", "status"),
    )


def downgrade():
    op.drop_table("dora_incident_classification_framework")
    op.drop_table("dora_penetration_test")
    op.drop_table("dora_ict_risk_register")
    op.drop_table("dora_third_party_provider")
    op.drop_table("dora_tic_incident")
