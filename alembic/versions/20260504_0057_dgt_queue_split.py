"""split DGT queue state out of source_revision

# Revision ID: 20260504_0057_dgt_queue_split
# Revises: 20260504_0056_modelo_articulo_provenance
# Create Date: 2026-05-04 12:30:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260504_0057_dgt_queue_split"
down_revision = "20260504_0056_modelo_articulo_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS dgt_queue (
                id SERIAL PRIMARY KEY,
                worker_name TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                dgt_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                queued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                processed_at TIMESTAMPTZ,
                UNIQUE (worker_name, source_entity_id)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE dgt_queue
                ADD CONSTRAINT ck_dgt_queue_status
                CHECK (status IN ('pending', 'processed', 'empty'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_dgt_queue_pending ON dgt_queue(worker_name, status, id)"
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO dgt_queue (worker_name, source_entity_id, dgt_url, status, queued_at, processed_at)
            SELECT
                worker_name,
                source_entity_id,
                dgt_url,
                CASE
                    WHEN content_hash_sha256 = 'pending' THEN 'pending'
                    WHEN content_hash_sha256 = 'empty' THEN 'empty'
                    ELSE 'processed'
                END,
                fetched_at,
                CASE
                    WHEN content_hash_sha256 = 'pending' THEN NULL
                    ELSE fetched_at
                END
            FROM source_revision
            WHERE source_entity_tipo = 'consulta'
              AND dgt_url IS NOT NULL
            ON CONFLICT (worker_name, source_entity_id) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM source_revision
            WHERE source_entity_tipo = 'consulta'
              AND dgt_url IS NOT NULL
              AND content_hash_sha256 !~ '^[0-9a-f]{64}$'
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_dgt_queue_pending"))
    op.execute(
        sa.text(
            "ALTER TABLE dgt_queue DROP CONSTRAINT IF EXISTS ck_dgt_queue_status"
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS dgt_queue"))
