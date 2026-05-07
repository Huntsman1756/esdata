-- Dead-letter queue for persistently failing worker syncs
-- Entities that exceed max retries are moved here for manual review

CREATE TABLE sync_dead_letter (
    id              SERIAL PRIMARY KEY,
    worker_name     TEXT NOT NULL,            -- which worker failed
    entity_id       TEXT NOT NULL,            -- which entity/document failed
    entity_type     TEXT NOT NULL,            -- 'norma', 'articulo', 'doctrina', etc.
    error_message   TEXT NOT NULL,            -- last error message
    error_traceback TEXT,                     -- abbreviated traceback
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 3,
    first_failed_at TEXT NOT NULL,            -- when first failure occurred
    last_failed_at  TEXT NOT NULL,            -- when last failure occurred
    resolved        INTEGER NOT NULL DEFAULT 0,
    resolved_at     TEXT,
    resolved_by     TEXT,                     -- human who resolved it
    notes           TEXT,                     -- resolution notes
    created_at      TEXT NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dead_letter_worker ON sync_dead_letter(worker_name, resolved);
CREATE INDEX IF NOT EXISTS idx_dead_letter_entity ON sync_dead_letter(entity_type, entity_id);
