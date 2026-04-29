"""add PRIIPs and LIVMC data model tables.

Creates:
- priips_kid: Key Information Document for PRIIPs products
- priips_product: PRIIPs-covered products
- livmc_client_protection: investor protection (LIVMC)
- livmc_voice_procedure: voice and complaint procedures (LivMC Art. 10)

# Revision ID: 20260428_0043_priips_livmc_models
# Revises: 20260428_0042_dora_models
# Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0043_priips_livmc_models"
down_revision = "20260428_0042_dora_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- priips_kid: Key Information Document ---
    op.create_table(
        "priips_kid",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_type", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("risk_scale", sa.Integer(), nullable=True),
        sa.Column("cost_impact", sa.JSON(), nullable=True),
        sa.Column("negative_scenario_returns", sa.JSON(), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_priips_kid_product", "product_id"),
        sa.Index("ix_priips_kid_risk", "risk_scale"),
        sa.Index("ix_priips_kid_status", "status"),
    )

    # --- priips_product: PRIIPs-covered products ---
    op.create_table(
        "priips_product",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issuer_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.Text(), nullable=True),
        sa.Column("underlying_assets", sa.JSON(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("min_investment", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("distribution_channels", sa.JSON(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_priips_product_issuer", "issuer_id"),
        sa.Index("ix_priips_product_currency", "currency"),
        sa.Index("ix_priips_product_status", "status"),
    )

    # --- livmc_client_protection: investor protection ---
    op.create_table(
        "livmc_client_protection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("protection_type", sa.Text(), nullable=True),
        sa.Column("provider_id", sa.Integer(), nullable=True),
        sa.Column("coverage_amount", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_livmc_cp_client", "client_id"),
        sa.Index("ix_livmc_cp_type", "protection_type"),
        sa.Index("ix_livmc_cp_status", "status"),
    )

    # --- livmc_voice_procedure: voice and complaint procedures ---
    op.create_table(
        "livmc_voice_procedure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("procedure_type", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("next_review", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_livmc_vp_entity", "entity_id"),
        sa.Index("ix_livmc_vp_type", "procedure_type"),
        sa.Index("ix_livmc_vp_status", "status"),
    )


def downgrade():
    op.drop_table("livmc_voice_procedure")
    op.drop_table("livmc_client_protection")
    op.drop_table("priips_product")
    op.drop_table("priips_kid")
