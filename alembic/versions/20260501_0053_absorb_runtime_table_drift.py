"""Absorb runtime DDL drift: sync_log and source_revision become migration-owned.

Hace que Alembic sea la fuente de verdad para tablas que hasta ahora se creaban
en runtime via `_ensure_sync_log_table` (apps/workers/boe.py, apps/workers/eurlex.py)
y `ensure_source_revision_table` (apps/workers/change_detection.py).

Crea las tablas con `CREATE TABLE IF NOT EXISTS` para ser idempotente sobre
despliegues que ya las tienen creadas por el path runtime. Tras esta migracion,
los helpers se convierten en no-op defensivo (solo SQLite/test).

Reversible: el downgrade NO borra las tablas (contendrian datos historicos);
el rollback semantico es revertir el codigo a la version anterior y dejar que
los helpers sigan creando bajo demanda.

# Revision ID: 20260501_0053_absorb_runtime_table_drift
# Revises: 20260430_0052_onda2_missing_tables
# Create Date: 2026-05-01 00:00:00
"""

from alembic import op

revision = "20260501_0053_absorb_runtime_table_drift"
down_revision = "20260430_0052_onda2_missing_tables"
branch_labels = None
depends_on = None


def upgrade():
    # --- sync_log ---
    # Schema canonico: union de columnas usadas por workers BOE, EUR-Lex y otros.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_log (
            id SERIAL PRIMARY KEY,
            worker TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ,
            status TEXT NOT NULL,
            bloques_processed INTEGER,
            articulos_upserted INTEGER,
            documentos_processed INTEGER,
            documentos_upserted INTEGER,
            doctrina_links_created INTEGER,
            rows_processed INTEGER,
            errors INTEGER DEFAULT 0,
            duration_ms INTEGER,
            error_msg TEXT
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sync_log_worker_started "
        "ON sync_log(worker, started_at DESC)"
    )

    # --- source_revision ---
    # Schema "nueva" de change_detection.py. El path legacy
    # (worker/entity_type/entity_id/source_hash) queda fuera de migracion;
    # no se introduce aqui para no perpetuar drift.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS source_revision (
            id SERIAL PRIMARY KEY,
            worker_name TEXT NOT NULL,
            source_entity_tipo TEXT NOT NULL,
            source_entity_id TEXT NOT NULL,
            content_hash_sha256 TEXT NOT NULL,
            etag TEXT,
            last_modified TEXT,
            content_length INTEGER,
            fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            dgt_url TEXT,
            UNIQUE (worker_name, source_entity_tipo, source_entity_id)
        )
        """
    )
    op.execute(
        "ALTER TABLE source_revision ADD COLUMN IF NOT EXISTS dgt_url TEXT"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_source_revision_worker_entity "
        "ON source_revision(worker_name, source_entity_tipo, source_entity_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_source_revision_pending_dgt "
        "ON source_revision(worker_name, source_entity_tipo, content_hash_sha256) "
        "WHERE content_hash_sha256 = 'pending' AND dgt_url IS NOT NULL"
    )


def downgrade():
    # No droppear: tablas pueden contener historico operativo (sync_log) o
    # estado de revisiones (source_revision). El rollback semantico es revertir
    # el codigo asociado.
    pass
