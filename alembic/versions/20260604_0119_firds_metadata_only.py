"""make ESMA FIRDS metadata-only

Revision ID: 20260604_0119_firds_metadata_only
Revises: 20260604_0118_promote_193_boe_25389_normativa
Create Date: 2026-06-04

Purge the bounded DLTINS instrument sample and keep only official ESMA FIRDS
file metadata. Instrument-level ISIN data is intentionally out of scope.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260604_0119_firds_metadata_only"
down_revision = "20260604_0118_promote_193_boe_25389_normativa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM esma_firds_instrument"))
    bind.execute(
        sa.text(
            """
            UPDATE esma_firds_file
            SET downloaded = false,
                processed = false,
                verified = false,
                completeness = 'parcial',
                updated_at = now()
            """
        )
    )


def downgrade() -> None:
    # Instrument-level FIRDS rows cannot be reconstructed safely from a purge.
    pass
