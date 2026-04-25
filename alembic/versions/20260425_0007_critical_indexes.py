"""add critical indexes for sync_log, articulo, version_articulo, documento_fragmento

Revision ID: 20260425_0007_critical_indexes
Revises: 20260425_0006_eval_history
Create Date: 2026-04-25 00:00:00

Indexes:
  - sync_log(worker), sync_log(started_at DESC), sync_log(worker, started_at DESC)
    → status endpoint queries by worker name
  - articulo(norma_id) → FK lookup from version_articulo
  - version_articulo(articulo_id), version_articulo(articulo_id, vigente_desde DESC)
    → latest version subquery in search
  - documento_articulo(documento_id) → doctrina detail endpoint
  - documento_fragmento(documento_origen_tipo, documento_origen_id)
    → search endpoints chunk lookup

Dialect: PostgreSQL only (indexes are no-ops on SQLite).
"""

from alembic import op

revision = "20260425_0007_critical_indexes"
down_revision = "20260425_0006_eval_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sync_log_worker
            ON sync_log(worker)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sync_log_started_at
            ON sync_log(started_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sync_log_worker_started
            ON sync_log(worker, started_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_articulo_norma_id
            ON articulo(norma_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_version_articulo_articulo_id
            ON version_articulo(articulo_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_version_articulo_articulo_vigente
            ON version_articulo(articulo_id, vigente_desde DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_articulo_documento
            ON documento_articulo(documento_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_fragmento_origen_tipo_id
            ON documento_fragmento(documento_origen_tipo, documento_origen_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_sync_log_worker")
    op.execute("DROP INDEX IF EXISTS idx_sync_log_started_at")
    op.execute("DROP INDEX IF EXISTS idx_sync_log_worker_started")
    op.execute("DROP INDEX IF EXISTS idx_articulo_norma_id")
    op.execute("DROP INDEX IF EXISTS idx_version_articulo_articulo_id")
    op.execute("DROP INDEX IF EXISTS idx_version_articulo_articulo_vigente")
    op.execute("DROP INDEX IF EXISTS idx_documento_articulo_documento")
    op.execute("DROP INDEX IF EXISTS idx_documento_fragmento_origen_tipo_id")
