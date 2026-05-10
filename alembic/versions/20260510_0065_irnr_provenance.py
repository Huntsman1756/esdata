"""add IRNR provenance columns

Revision ID: 20260510_0065_irnr_provenance
Revises: 20260510_0064_security_closure
Create Date: 2026-05-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260510_0065_irnr_provenance"
down_revision = "20260510_0064_security_closure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("irnr_instruccion", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("irnr_instruccion", sa.Column("source_family", sa.Text(), nullable=True))

    op.add_column("irnr_withholding_rate", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("irnr_withholding_rate", sa.Column("source_family", sa.Text(), nullable=True))
    op.add_column("irnr_withholding_rate", sa.Column("effective_date", sa.Date(), nullable=True))
    op.add_column("irnr_withholding_rate", sa.Column("legal_basis", sa.Text(), nullable=True))
    op.add_column("irnr_withholding_rate", sa.Column("uncertainty_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("irnr_withholding_rate", "uncertainty_notes")
    op.drop_column("irnr_withholding_rate", "legal_basis")
    op.drop_column("irnr_withholding_rate", "effective_date")
    op.drop_column("irnr_withholding_rate", "source_family")
    op.drop_column("irnr_withholding_rate", "source_url")

    op.drop_column("irnr_instruccion", "source_family")
    op.drop_column("irnr_instruccion", "source_url")
