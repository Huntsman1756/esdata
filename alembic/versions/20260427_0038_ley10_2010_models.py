"""add Ley 10/2010 (PBC/FT) data model tables.

Creates:
- pbc_obligated_subject: obligated subjects under anti-money laundering law
- pbc_internal_control: internal controls for AML compliance
- suspicious_activity_report: SAR/MAR (suspicious activity reports)
- beneficial_owner_record: beneficial ownership records

Revision ID: 20260427_0038_ley10_2010_models
Revises: 20260427_0037_dac8_dac9_models
Create Date: 2026-04-27 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260427_0038_ley10_2010_models"
down_revision = "20260427_0037_dac8_dac9_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- pbc_obligated_subject: obligated subjects under Ley 10/2010 ---
    op.create_table(
        "pbc_obligated_subject",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_type", sa.Text(), nullable=True),
        sa.Column("tin", sa.Text(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("supervisory_authority", sa.Text(), nullable=True),
        sa.Column("pbc_license", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_pbc_obligated_subject_type", "subject_type"),
        sa.Index("ix_pbc_obligated_subject_tin", "tin"),
        sa.Index("ix_pbc_obligated_subject_status", "status"),
    )

    # --- pbc_internal_control: internal AML controls ---
    op.create_table(
        "pbc_internal_control",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("obligated_subject_id", sa.Integer(), nullable=True),
        sa.Column("risk_assessment_date", sa.Date(), nullable=True),
        sa.Column("compliance_officer", sa.Text(), nullable=True),
        sa.Column("internal_reporting_channel", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("training_program", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("audit_trail", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_pbc_internal_control_subject", "obligated_subject_id"),
    )

    # --- suspicious_activity_report: SAR/MAR ---
    op.create_table(
        "suspicious_activity_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("obligated_subject_id", sa.Integer(), nullable=True),
        sa.Column("submission_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'filed'::text")),
        sa.Column("sepblac_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_suspicious_activity_report_subject", "obligated_subject_id"),
        sa.Index("ix_suspicious_activity_report_status", "status"),
        sa.Index("ix_suspicious_activity_report_severity", "severity"),
    )

    # --- beneficial_owner_record: beneficial ownership ---
    op.create_table(
        "beneficial_owner_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("ownership_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("acquisition_date", sa.Date(), nullable=True),
        sa.Column("verification_method", sa.Text(), nullable=True),
        sa.Column("verification_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_beneficial_owner_record_entity", "entity_id"),
    )


def downgrade():
    op.drop_table("beneficial_owner_record")
    op.drop_table("suspicious_activity_report")
    op.drop_table("pbc_internal_control")
    op.drop_table("pbc_obligated_subject")
