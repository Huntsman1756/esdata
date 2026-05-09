"""add dead letter table

Revision ID: 20260509_0060_dead_letter
Revises: 987eafbc4c83
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260509_0060_dead_letter'
down_revision = '987eafbc4c83'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sync_dead_letter',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('worker_name', sa.String(255), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('first_failed_at', sa.String(50), nullable=True),
        sa.Column('last_failed_at', sa.String(50), nullable=True),
        sa.Column('resolved_at', sa.String(50), nullable=True),
        sa.Column('resolved_by', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint('worker_name', 'entity_id', name='uq_dead_letter_worker_entity'),
    )
    op.create_index('ix_dead_letter_worker_resolved', 'sync_dead_letter', ['worker_name', 'resolved'])
    op.create_index('ix_dead_letter_last_failed', 'sync_dead_letter', ['last_failed_at'])


def downgrade() -> None:
    op.drop_index('ix_dead_letter_last_failed', table_name='sync_dead_letter')
    op.drop_index('ix_dead_letter_worker_resolved', table_name='sync_dead_letter')
    op.drop_table('sync_dead_letter')
