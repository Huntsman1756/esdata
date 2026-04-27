-- Fiscal calendar — deadlines for AEAT models by year
-- Data source: AEAT Calendario del Contribuyente

CREATE TABLE IF NOT EXISTS fiscal_calendar (
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
