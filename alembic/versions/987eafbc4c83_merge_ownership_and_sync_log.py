"""merge_ownership_and_sync_log

# Revision ID: 987eafbc4c83
# Revises: 20260426_0013_ownership, 20260427_0031_sync_log_operability_contract
# Create Date: 2026-04-27 10:44:05.530490
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '987eafbc4c83'
down_revision = ('20260426_0013_ownership', '20260427_0031_sync_log_operability_contract')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
