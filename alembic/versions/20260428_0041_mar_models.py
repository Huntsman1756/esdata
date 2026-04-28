"""add MAR (Market Abuse Regulation) data model tables.

Creates:
- mar_insider_transaction: PPI transactions (MAR Art. 19)
- mar_suspicious_transaction_report: STR submissions to CNMV
- mar_market_manipulation_indicator: manipulation pattern detection
- mar_insider_communication: insider communication tracking

Revision ID: 20260428_0041_mar_models
Revises: 20260428_0040_mifid_mir_models
Create Date: 2026-04-28 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260428_0041_mar_models"
down_revision = "20260428_0040_mifid_mir_models"
branch_labels = None
depends_on = None


def upgrade():
    # --- mar_insider_transaction: PPI transactions (MAR Art. 19) ---
    op.create_table(
        "mar_insider_transaction",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ppi_name", sa.Text(), nullable=True),
        sa.Column("ppi_role", sa.Text(), nullable=True),
        sa.Column("instrument", sa.Text(), nullable=True),
        sa.Column("transaction_type", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("value_eur", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("price", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("date_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'reported'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mar_insider_txn_ppi", "ppi_name"),
        sa.Index("ix_mar_insider_txn_instrument", "instrument"),
        sa.Index("ix_mar_insider_txn_status", "status"),
    )

    # --- mar_suspicious_transaction_report: STR to CNMV ---
    op.create_table(
        "mar_suspicious_transaction_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("instrument", sa.Text(), nullable=True),
        sa.Column("pattern_description", sa.Text(), nullable=True),
        sa.Column("detection_method", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
        sa.Column("submitted_to_cnmv", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cnmv_reference", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'under_review'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mar_str_entity", "entity_id"),
        sa.Index("ix_mar_str_instrument", "instrument"),
        sa.Index("ix_mar_str_status", "status"),
    )

    # --- mar_market_manipulation_indicator: manipulation patterns ---
    op.create_table(
        "mar_market_manipulation_indicator",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pattern_type", sa.Text(), nullable=True),
        sa.Column("instrument", sa.Text(), nullable=True),
        sa.Column("time_window", sa.Text(), nullable=True),
        sa.Column("volume_anomaly_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("price_anomaly_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'::text")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mar_mmi_pattern", "pattern_type"),
        sa.Index("ix_mar_mmi_instrument", "instrument"),
        sa.Index("ix_mar_mmi_status", "status"),
    )

    # --- mar_insider_communication: insider info tracking ---
    op.create_table(
        "mar_insider_communication",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("receiver_id", sa.Integer(), nullable=True),
        sa.Column("content_summary", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("inside_info_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_mar_ic_sender", "sender_id"),
        sa.Index("ix_mar_ic_receiver", "receiver_id"),
        sa.Index("ix_mar_ic_ts", "timestamp"),
    )


def downgrade():
    op.drop_table("mar_insider_communication")
    op.drop_table("mar_market_manipulation_indicator")
    op.drop_table("mar_suspicious_transaction_report")
    op.drop_table("mar_insider_transaction")
