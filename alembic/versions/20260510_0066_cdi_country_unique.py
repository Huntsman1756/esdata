"""add unique constraint for CDI country upserts

Revision ID: 20260510_0066_cdi_country_unique
Revises: 20260510_0065_irnr_provenance
Create Date: 2026-05-10
"""

from alembic import op


revision = "20260510_0066_cdi_country_unique"
down_revision = "20260510_0065_irnr_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_irs_dta_convention_pais_origen",
        "irs_dta_convention",
        ["pais_origen"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_irs_dta_convention_pais_origen",
        "irs_dta_convention",
        type_="unique",
    )
