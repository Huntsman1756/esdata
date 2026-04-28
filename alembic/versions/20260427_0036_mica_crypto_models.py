"""add MiCA and crypto-asset data model tables.

Creates:
- casp: crypto-asset service providers
- crypto_asset: crypto-asset classes under MiCA
- tokenized_asset: tokenized assets under MiCA
- wallet_custodian: wallet custodians
- crypto_transaction: crypto transactions for DAC8/DAC9 reporting

Revision ID: 20260427_0036_mica_crypto_models
Revises: 20260427_0035_multi_source_embeddings
Create Date: 2026-04-27 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260427_0036_mica_crypto_models"
down_revision = "20260427_0035_multi_source_embeddings"
branch_labels = None
depends_on = None


def upgrade():
    # --- casp: crypto-asset service provider ---
    op.create_table(
        "casp",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("registration_number", sa.Text(), nullable=True, unique=True),
        sa.Column("home_member_state", sa.Text(), nullable=True),
        sa.Column("passport_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("services_offered", sa.JSON(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_casp_home_state", "home_member_state"),
        sa.Index("ix_casp_status", "status"),
    )

    # --- crypto_asset: crypto-asset classes under MiCA ---
    op.create_table(
        "crypto_asset",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("reference_uid", sa.Text(), nullable=True),
        sa.Column("issuer_jurisdiction", sa.Text(), nullable=True),
        sa.Column("is_sha", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("market_value_eur", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("holders_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_crypto_asset_type", "asset_type"),
        sa.Index("ix_crypto_asset_sha", "is_sha"),
        sa.Index("ix_crypto_asset_status", "status"),
    )

    # --- tokenized_asset: tokenized assets under MiCA ---
    op.create_table(
        "tokenized_asset",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("underlying_type", sa.Text(), nullable=True),
        sa.Column("issuer_id", sa.Integer(), nullable=True),
        sa.Column("face_value", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("listing_date", sa.Date(), nullable=True),
        sa.Column("regulated_market", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_tokenized_asset_type", "underlying_type"),
        sa.Index("ix_tokenized_asset_status", "status"),
    )

    # --- wallet_custodian: wallet custodians ---
    op.create_table(
        "wallet_custodian",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("wallet_type", sa.Text(), nullable=True),
        sa.Column("custody_mechanism", sa.Text(), nullable=True),
        sa.Column("insurance_coverage", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("audit_frequency", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_wallet_custodian_type", "wallet_type"),
        sa.Index("ix_wallet_custodian_status", "status"),
    )

    # --- crypto_transaction: crypto transactions for DAC8/DAC9 ---
    op.create_table(
        "crypto_transaction",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_wallet", sa.Text(), nullable=True),
        sa.Column("receiver_wallet", sa.Text(), nullable=True),
        sa.Column("sender_jurisdiction", sa.Text(), nullable=True),
        sa.Column("receiver_jurisdiction", sa.Text(), nullable=True),
        sa.Column("asset_type", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("value_eur", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reporting_period", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_crypto_transaction_asset", "asset_type"),
        sa.Index("ix_crypto_transaction_period", "reporting_period"),
        sa.Index("ix_crypto_transaction_sender", "sender_wallet"),
        sa.Index("ix_crypto_transaction_receiver", "receiver_wallet"),
    )


def downgrade():
    op.drop_table("crypto_transaction")
    op.drop_table("wallet_custodian")
    op.drop_table("tokenized_asset")
    op.drop_table("crypto_asset")
    op.drop_table("casp")
