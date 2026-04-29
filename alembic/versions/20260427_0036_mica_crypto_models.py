"""add MiCA and crypto-asset service tables

- casp: crypto-asset service providers (ESMA registry)
- crypto_asset: tokenized and crypto-asset classes under MiCA
- tokenized_asset: asset-referenced and e-money tokens
- wallet_custodian: custody providers for crypto wallets
- crypto_transaction: transaction records for DAC8/DAC9 reporting
"""

Revision ID: 20260427_0036_mica_crypto_models
Revises: 20260427_0035_multi_source_embeddings
Create Date: 2026-04-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa
revision = "20260427_0036_mica_crypto_models"
down_revision = "20260427_0035_multi_source_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- casp: crypto-asset service providers ---
    op.create_table(
        "casp",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("home_member_state", sa.Text(), nullable=True, comment="ISO 3166-1 alpha-2"),
        sa.Column("passport_active", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("services_offered", sa.Text(), nullable=True, comment="JSON array: custody, exchange, execution, payment"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active", comment="active, suspended, revoked"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_number", "home_member_state", name="uq_casp_reg"),
    )
    op.create_index("idx_casp_name", "casp", ["name"])
    op.create_index("idx_casp_status", "casp", ["status"])

    # --- crypto_asset: classes of crypto-assets under MiCA ---
    op.create_table(
        "crypto_asset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_type", sa.Text(), nullable=False, comment="asset-referenced, e-money, utility, other"),
        sa.Column("reference_uid", sa.Text(), nullable=True, comment="Unique identifier from issuer"),
        sa.Column("issuer_jurisdiction", sa.Text(), nullable=True, comment="ISO 3166-1 alpha-2"),
        sa.Column("is_sha", sa.Boolean(), nullable=False, server_default="0", comment="Significant crypto-asset"),
        sa.Column("market_value_eur", sa.Numeric(precision=28, scale=2), nullable=True),
        sa.Column("holders_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_crypto_asset_type", "crypto_asset", ["asset_type"])
    op.create_index("idx_crypto_asset_sha", "crypto_asset", ["is_sha"])
    op.create_index("idx_crypto_asset_status", "crypto_asset", ["status"])

    # --- tokenized_asset: tokenized traditional assets under MiCA ---
    op.create_table(
        "tokenized_asset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("underlying_type", sa.Text(), nullable=False, comment="equity, bond, fund, real-estate, other"),
        sa.Column("issuer_id", sa.Integer(), nullable=True),
        sa.Column("face_value", sa.Numeric(precision=28, scale=2), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=28, scale=2), nullable=True),
        sa.Column("listing_date", sa.Date(), nullable=True),
        sa.Column("regulated_market", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tokenized_asset_type", "tokenized_asset", ["underlying_type"])
    op.create_index("idx_tokenized_asset_status", "tokenized_asset", ["status"])

    # --- wallet_custodian: custody providers ---
    op.create_table(
        "wallet_custodian",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True, comment="Links to empresa table if registered entity"),
        sa.Column("wallet_type", sa.Text(), nullable=False, comment="hot, cold, hybrid"),
        sa.Column("custody_mechanism", sa.Text(), nullable=True, comment="multi-sig, MPC, hardware, etc."),
        sa.Column("insurance_coverage", sa.Numeric(precision=28, scale=2), nullable=True),
        sa.Column("audit_frequency", sa.Text(), nullable=True, comment="monthly, quarterly, annual"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wallet_custodian_type", "wallet_custodian", ["wallet_type"])
    op.create_index("idx_wallet_custodian_status", "wallet_custodian", ["status"])

    # --- crypto_transaction: transaction records for DAC8/DAC9 ---
    op.create_table(
        "crypto_transaction",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sender_wallet", sa.Text(), nullable=True, comment="Sender wallet address (pseudonymized)"),
        sa.Column("receiver_wallet", sa.Text(), nullable=True, comment="Receiver wallet address (pseudonymized)"),
        sa.Column("sender_jurisdiction", sa.Text(), nullable=True, comment="ISO 3166-1 alpha-2 of sender"),
        sa.Column("receiver_jurisdiction", sa.Text(), nullable=True, comment="ISO 3166-1 alpha-2 of receiver"),
        sa.Column("asset_type", sa.Text(), nullable=False, comment="asset-referenced, e-money, utility, other"),
        sa.Column("amount", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("value_eur", sa.Numeric(precision=28, scale=2), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reporting_period", sa.Text(), nullable=True, comment="YYYY-MM for DAC8 reporting"),
        sa.Column("status", sa.Text(), nullable=False, server_default="reported", comment="reported, amended, rejected"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_crypto_transaction_asset", "crypto_transaction", ["asset_type"])
    op.create_index("idx_crypto_transaction_period", "crypto_transaction", ["reporting_period"])
    op.create_index("idx_crypto_transaction_timestamp", "crypto_transaction", ["timestamp"])
    op.create_index("idx_crypto_transaction_status", "crypto_transaction", ["status"])


def downgrade() -> None:
    op.drop_table("crypto_transaction")
    op.drop_table("wallet_custodian")
    op.drop_table("tokenized_asset")
    op.drop_table("crypto_asset")
    op.drop_table("casp")
