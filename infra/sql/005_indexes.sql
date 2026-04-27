-- Critical indexes for performance and data integrity
-- Applied via: psql "$(DATABASE_URL)" -f infra/sql/005_indexes.sql
-- or: make db-upgrade (Alembic migration 006 creates these)

-- sync_log: status endpoint queries by worker name (12 workers, full scan without index)
CREATE INDEX IF NOT EXISTS idx_sync_log_worker
    ON sync_log(worker);

-- sync_log: order by started_at DESC for latest run
CREATE INDEX IF NOT EXISTS idx_sync_log_started_at
    ON sync_log(started_at DESC);

-- Combined index for status endpoint: (worker, started_at DESC)
CREATE INDEX IF NOT EXISTS idx_sync_log_worker_started
    ON sync_log(worker, started_at DESC);

-- articulo: FK lookup from version_articulo → articulo (JOIN on articulo_id)
CREATE INDEX IF NOT EXISTS idx_articulo_norma_id
    ON articulo(norma_id);

-- version_articulo: FK lookup from version_articulo → articulo
CREATE INDEX IF NOT EXISTS idx_version_articulo_articulo_id
    ON version_articulo(articulo_id);

-- version_articulo: query for latest version per article (subquery in search)
CREATE INDEX IF NOT EXISTS idx_version_articulo_articulo_vigente
    ON version_articulo(articulo_id, vigente_desde DESC);

-- documento_articulo: lookup by documento_id (doctrina detail endpoint)
CREATE INDEX IF NOT EXISTS idx_documento_articulo_documento
    ON documento_articulo(documento_id);

-- documento_fragmento: lookup by document origin (search endpoints)
-- Skipped in docker-init; created via Alembic migration instead
-- CREATE INDEX IF NOT EXISTS idx_documento_fragmento_origen_tipo_id
--     ON documento_fragmento(documento_origen_tipo, documento_origen_id);
