-- Regulatory changes tracking table
-- Tracks detected changes from official sources (BOE, AEAT, EUR-Lex, AEPD, BDE, etc.)
-- Used by regulatory_watch worker for source-of-truth monitoring

CREATE TABLE IF NOT EXISTS regulatory_changes (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,            -- 'boe', 'aeat', 'eurlex', 'aepd', 'bde', 'dgt'
    norma           TEXT NOT NULL,            -- e.g. 'L37/1992', 'L35/2006', 'EUR-CELEX-32014L0065'
    change_type     TEXT NOT NULL,            -- 'rate_change', 'deadline_change', 'new_norm', 'repeal', 'amendment', 'new_rate'
    description     TEXT NOT NULL,
    detected_at     TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'warning',  -- 'info', 'warning', 'critical'
    reviewed        INTEGER NOT NULL DEFAULT 0,
    reviewed_at     TEXT,
    reviewed_by     TEXT,
    created_at      TEXT NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reg_changes_source ON regulatory_changes(source, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_reg_changes_norma ON regulatory_changes(norma, detected_at DESC);
