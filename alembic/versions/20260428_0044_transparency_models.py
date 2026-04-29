"""add transparency of issuers data model tables.

Creates:
- transparency_issuer: issuers subject to transparency directive
- transparency_regulated_information: regulated information publications
- transparency_voting_rights: voting rights holdings
- transparency_internal_rule: internal rules on relevant information

# Revision ID: 20260428_0044_transparency_models
# Revises: 20260428_0043_priips_livmc_models
# Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0044_transparency_models"
down_revision = "20260428_0043_priips_livmc_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- transparency_issuer: transparency directive issuers ---
    op.create_table(
        "transparency_issuer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issuer_id", sa.Integer(), nullable=True),
        sa.Column("listing_market", sa.Text(), nullable=True),
        sa.Column("ticker", sa.Text(), nullable=True),
        sa.Column("reporting_frequency", sa.Text(), nullable=True),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_transp_issuer_market", "listing_market"),
        sa.Index("ix_transp_issuer_ticker", "ticker"),
        sa.Index("ix_transp_issuer_status", "status"),
    )

    # --- transparency_regulated_information: regulated info publications ---
    op.create_table(
        "transparency_regulated_information",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issuer_id", sa.Integer(), nullable=True),
        sa.Column("info_type", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("content_url", sa.Text(), nullable=True),
        sa.Column("filing_reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'published'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_transp_ri_issuer", "issuer_id"),
        sa.Index("ix_transp_ri_type", "info_type"),
        sa.Index("ix_transp_ri_date", "publication_date"),
        sa.Index("ix_transp_ri_status", "status"),
    )

    # --- transparency_voting_rights: voting rights holdings ---
    op.create_table(
        "transparency_voting_rights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issuer_id", sa.Integer(), nullable=True),
        sa.Column("shareholder_id", sa.Integer(), nullable=True),
        sa.Column("voting_rights_pct", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("date_acquired", sa.Date(), nullable=True),
        sa.Column("date_reported", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_transp_vr_issuer", "issuer_id"),
        sa.Index("ix_transp_vr_shareholder", "shareholder_id"),
        sa.Index("ix_transp_vr_date", "date_acquired"),
        sa.Index("ix_transp_vr_status", "status"),
    )

    # --- transparency_internal_rule: internal rules on relevant info ---
    op.create_table(
        "transparency_internal_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("designated_persons", sa.JSON(), nullable=True),
        sa.Column("internal_procedure", sa.Text(), nullable=True),
        sa.Column("retention_period", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_transp_ir_entity", "entity_id"),
        sa.Index("ix_transp_ir_status", "status"),
    )


def downgrade():
    op.drop_table("transparency_internal_rule")
    op.drop_table("transparency_voting_rights")
    op.drop_table("transparency_regulated_information")
    op.drop_table("transparency_issuer")
