-- Fiscal calendar — deadlines for AEAT models by year
-- Data source: AEAT Calendario del Contribuyente

-- Alert table: tracks data freshness SLA breaches for human review
CREATE TABLE data_freshness_alerts (
    id              SERIAL PRIMARY KEY,
    source_id       TEXT NOT NULL,
    alert_level     TEXT NOT NULL DEFAULT 'warning',  -- 'warning', 'critical', 'resolved'
    stale_since     TEXT NOT NULL,
    expected_interval TEXT NOT NULL,  -- e.g. 'daily', 'weekly'
    last_success_at TEXT,
    message         TEXT NOT NULL,
    acknowledged    INTEGER NOT NULL DEFAULT 0,
    acknowledged_at TEXT,
    created_at      TEXT NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_freshness_alerts_source ON data_freshness_alerts(source_id, stale_since DESC);
CREATE INDEX IF NOT EXISTS idx_freshness_alerts_level ON data_freshness_alerts(alert_level, acknowledged);

CREATE TABLE fiscal_calendar (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    modelo_codigo   TEXT NOT NULL,
    date_start      DATE NOT NULL,
    date_end        DATE NOT NULL,
    description     TEXT NOT NULL,
    who_applies     TEXT,                       -- 'autonomos', 'sociedades', 'todos'
    source          TEXT,                       -- AEAT Calendario Contribuyente reference
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, modelo_codigo, date_start, date_end)
);

CREATE INDEX IF NOT EXISTS idx_fiscal_calendar_year ON fiscal_calendar(year);
CREATE INDEX IF NOT EXISTS idx_fiscal_calendar_modelo ON fiscal_calendar(year, modelo_codigo);
