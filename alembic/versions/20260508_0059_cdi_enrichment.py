"""add CDI enrichment columns

Revision ID: 20260508_0059_cdi_enrichment
Revises: 20260504_0058_row_completeness_provenance
Create Date: 2026-05-08

Add columns to irs_dta_convention for Hacienda table data:
- fecha_rubrica: date of rubrication
- boe_links: JSON array of BOE reference links
- pdf_urls: JSON array of PDF URLs from AEAT
- textos_sinteticos: JSON object of synthetic texts (retenciones, articulos)
"""

from alembic import op
import sqlalchemy as sa

revision = "20260508_0059_cdi_enrichment"
down_revision = "20260504_0058_row_completeness_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("irs_dta_convention", sa.Column("fecha_rubrica", sa.Date(), nullable=True))
    op.add_column("irs_dta_convention", sa.Column("boe_links", sa.JSON(), nullable=True))
    op.add_column("irs_dta_convention", sa.Column("pdf_urls", sa.JSON(), nullable=True))
    op.add_column("irs_dta_convention", sa.Column("textos_sinteticos", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("irs_dta_convention", "textos_sinteticos")
    op.drop_column("irs_dta_convention", "pdf_urls")
    op.drop_column("irs_dta_convention", "boe_links")
    op.drop_column("irs_dta_convention", "fecha_rubrica")
