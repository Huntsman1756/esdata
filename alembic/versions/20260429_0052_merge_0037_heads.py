"""merge 0037 heads: dac8_dac9_models and query_audit_log_grounding_fields.

# Revision ID: 20260429_0052_merge_0037_heads
# Parent 1: 20260428_0051_idd_solvency_models
# Parent 2: 20260427_0037a_query_audit_log_grounding_fields
# Create Date: 2026-04-29 00:00:00
"""

from alembic import op

revision = "20260429_0052_merge_0037_heads"
down_revision = "20260428_0051_idd_solvency_models"
branch_labels = None
depends_on = ("20260427_0037_dac8_dac9_models", "20260427_0037a_query_audit_log_grounding_fields")


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
