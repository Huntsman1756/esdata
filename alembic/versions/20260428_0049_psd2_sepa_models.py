"""Add PSD2/PSD3 and SEPA data model tables.

Creates:
- psd2_aspsp: account servicing payment service providers
- psd2_aisp: account information service providers
- psd2_pisp: payment initiation service providers
- psd2_consent: DSP consent records
- psd2_incident_report: PSD2 incident reports
- sepa_payment_rule: SEPA payment scheme rules

# Revision ID: 20260428_0049_psd2_sepa_models
# Revises: 20260428_0048_crd_brrd_emir_models
# Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0049_psd2_sepa_models"
down_revision = "20260428_0048_crd_brrd_emir_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- psd2_aspsp: account servicing payment service providers ---
    op.create_table(
        "psd2_aspsp",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("bic", sa.Text(), nullable=True),
        sa.Column("psd2_license", sa.Text(), nullable=True),
        sa.Column("strong_customer_auth_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("api_version", sa.Text(), nullable=True, server_default=sa.text("'v2'::text")),
        sa.Column("regulatory_status", sa.Text(), nullable=False, server_default=sa.text("'registered'::text")),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_psd2_aspsp_entity", "entity_id"),
    )

    # --- psd2_aisp: account information service providers ---
    op.create_table(
        "psd2_aisp",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("registration_id", sa.Text(), nullable=True),
        sa.Column("access_scope", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_psd2_aisp_entity", "entity_id"),
    )

    # --- psd2_pisp: payment initiation service providers ---
    op.create_table(
        "psd2_pisp",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("authorization_status", sa.Text(), nullable=False, server_default=sa.text("'authorized'::text")),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("psd3_transition_status", sa.Text(), nullable=True, server_default=sa.text("'not_started'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_psd2_pisp_entity", "entity_id"),
    )

    # --- psd2_consent: DSP consent records ---
    op.create_table(
        "psd2_consent",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("aspsp_id", sa.Integer(), nullable=True),
        sa.Column("consent_type", sa.Text(), nullable=False, server_default=sa.text("'AIS'::text")),
        sa.Column("accounts_accessed", sa.Text(), nullable=True),
        sa.Column("payment_count_limit", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_psd2_consent_aspsp", "aspsp_id"),
    )

    # --- psd2_incident_report: PSD2 incident reports ---
    op.create_table(
        "psd2_incident_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aspsp_id", sa.Integer(), nullable=True),
        sa.Column("incident_type", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=False, server_default=sa.text("'medium'::text")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reported_to_bde", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reported_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_psd2_incident_aspsp", "aspsp_id"),
    )

    # --- sepa_payment_rule: SEPA payment scheme rules ---
    op.create_table(
        "sepa_payment_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheme_version", sa.Text(), nullable=False),
        sa.Column("payment_type", sa.Text(), nullable=False),
        sa.Column("service_level", sa.Text(), nullable=False),
        sa.Column("local_instrument", sa.Text(), nullable=True),
        sa.Column("category_purpose", sa.Text(), nullable=True),
        sa.Column("cut_off_time", sa.Text(), nullable=True),
        sa.Column("settlement_days", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_table("sepa_payment_rule")
    op.drop_table("psd2_incident_report")
    op.drop_table("psd2_consent")
    op.drop_table("psd2_pisp")
    op.drop_table("psd2_aisp")
    op.drop_table("psd2_aspsp")
