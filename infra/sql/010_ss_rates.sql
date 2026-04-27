-- Social Security rates — contribution bases and rates
-- Data source: Seguridad Social / REI

CREATE TABLE IF NOT EXISTS ss_rates (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    category        TEXT NOT NULL,                    -- 'general', 'young', 'trainees', 'freelance'
    base_monthly    NUMERIC(12,2),                    -- monthly contribution base
    base_annual     NUMERIC(12,2),                    -- annual contribution base
    rate_common     NUMERIC(5,2),                     -- common contribution rate %
    rate_accident   NUMERIC(5,2),                     -- accident insurance rate % (varies by risk category)
    total_rate      NUMERIC(5,2),                     -- combined rate %
    source          TEXT,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, category)
);

CREATE INDEX IF NOT EXISTS idx_ss_rates_year ON ss_rates(year);
