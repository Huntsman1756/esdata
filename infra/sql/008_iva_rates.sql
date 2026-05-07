-- IVA rates — tax rates, surcharges, exemptions
-- Data source: Ley 37/1992 (LIVA)

CREATE TABLE iva_rates (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    territory       TEXT NOT NULL DEFAULT 'peninsular',  -- 'peninsular', 'canarias', 'ceuta_melilla'
    rate_type       TEXT NOT NULL,                    -- 'general', 'reducido', 'superreducido', 'especial'
    rate            NUMERIC(5,2) NOT NULL,            -- percentage
    applies_to      TEXT,                             -- description of applicable goods/services
    source          TEXT,                             -- legal reference (e.g. 'Ley 37/1992, art. 90')
    source_url      TEXT,                             -- direct URL to source document (BOE, AEAT, etc.)
    ingestion_timestamp TIMESTAMPTZ DEFAULT now(),    -- when this record was ingested
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, territory, rate_type)
);

CREATE TABLE iva_surcharges (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    vat_rate        NUMERIC(5,2),                     -- base IVA rate this surcharge applies to
    vat_rate_label  TEXT,                             -- e.g. 'tabaco'
    surcharge_rate  NUMERIC(5,2) NOT NULL,            -- percentage
    source          TEXT,
    source_url      TEXT,
    ingestion_timestamp TIMESTAMPTZ DEFAULT now(),
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, vat_rate, vat_rate_label)
);

CREATE TABLE iva_exemptions (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    category        TEXT NOT NULL,                    -- e.g. 'Servicios medicos y sanitarios'
    source          TEXT,                             -- legal reference
    source_url      TEXT,
    ingestion_timestamp TIMESTAMPTZ DEFAULT now(),
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, category)
);

CREATE INDEX IF NOT EXISTS idx_iva_rates_year ON iva_rates(year);
CREATE INDEX IF NOT EXISTS idx_iva_surcharges_year ON iva_surcharges(year);
CREATE INDEX IF NOT EXISTS idx_iva_exemptions_year ON iva_exemptions(year);
