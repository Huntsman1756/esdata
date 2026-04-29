-- Fiscal indicators — reference values used across tax calculations
-- Data source: PIR, IPREM, IRVM, minimums set by law each year

CREATE TABLE fiscal_indicators (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    indicator_type  TEXT NOT NULL,                    -- 'PIR', 'IPREM', 'IRVM', 'min_renta', 'min_work_income'
    amount          NUMERIC(12,2),                    -- annual amount
    monthly_amount  NUMERIC(12,2),                    -- monthly equivalent if applicable
    source          TEXT,                             -- legal reference
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, indicator_type)
);

CREATE INDEX IF NOT EXISTS idx_fiscal_indicators_year ON fiscal_indicators(year);
