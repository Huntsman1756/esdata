-- IRPF brackets, personal minimums, work income reductions
-- Data source: Ley 35/2006 (LIRPF)

CREATE TABLE IF NOT EXISTS irpf_brackets (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    bracket_type    TEXT NOT NULL,                    -- 'general', 'savings'
    territory       TEXT NOT NULL DEFAULT 'state',    -- 'state', or CCAA code
    from_amount     NUMERIC(12,2) NOT NULL,
    to_amount       NUMERIC(12,2),                    -- NULL = no upper limit
    rate            NUMERIC(5,2) NOT NULL,            -- percentage
    source          TEXT,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, bracket_type, territory, from_amount, to_amount)
);

CREATE TABLE IF NOT EXISTS irpf_personal_minimums (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    category        TEXT NOT NULL,                    -- 'taxpayer', 'descendants', 'ascendants', 'disability'
    subcategory     TEXT NOT NULL,                    -- 'general', 'age_65_plus', 'first', '33_to_65_percent', etc.
    amount          NUMERIC(12,2) NOT NULL,
    source          TEXT,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, category, subcategory)
);

CREATE TABLE IF NOT EXISTS irpf_work_income_reduction (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    rule_type       TEXT NOT NULL,                    -- 'scale', 'new_deduction'
    net_income_up_to NUMERIC(12,2),
    net_income_from NUMERIC(12,2),
    reduction       NUMERIC(12,2),                    -- fixed amount or max
    reduction_formula TEXT,                           -- formula when not a fixed amount
    other_income_max NUMERIC(12,2),
    phase_out_limit NUMERIC(12,2),
    phase_out_formula TEXT,
    source          TEXT,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, rule_type)
);

CREATE INDEX IF NOT EXISTS idx_irpf_brackets_year ON irpf_brackets(year);
CREATE INDEX IF NOT EXISTS idx_irpf_personal_minimums_year ON irpf_personal_minimums(year);
CREATE INDEX IF NOT EXISTS idx_irpf_work_income_reduction_year ON irpf_work_income_reduction(year);
