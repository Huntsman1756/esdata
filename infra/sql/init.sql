-- ============================================================
-- init.sql — Base schema for esdata PostgreSQL
-- Mounted as /docker-entrypoint-initdb.d/010_init.sql
-- ============================================================

-- Extensions (must be first)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;


CREATE EXTENSION IF NOT EXISTS pg_trgm;

ALTER TABLE version_articulo
ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

UPDATE version_articulo
SET search_vector = to_tsvector('spanish', COALESCE(texto, ''));

CREATE INDEX IF NOT EXISTS idx_version_articulo_search_vector
    ON version_articulo USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS idx_articulo_titulo_trgm
    ON articulo USING GIN (titulo gin_trgm_ops);

CREATE OR REPLACE FUNCTION update_version_articulo_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.texto, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_version_articulo_search_vector ON version_articulo;

CREATE TRIGGER trg_version_articulo_search_vector
BEFORE INSERT OR UPDATE OF texto ON version_articulo
FOR EACH ROW
EXECUTE FUNCTION update_version_articulo_search_vector();

-- Modelos AEAT y su relación con artículos legislativos
-- Fase 1: estructura base + top 6 modelos
-- Cada relación modelo_articulo requiere fuente oficial explícita.

CREATE TABLE aeat_modelo (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,        -- '100', '303', etc.
    nombre TEXT NOT NULL,               -- 'IRPF Declaración anual'
    periodo TEXT,                       -- 'anual', 'trimestral', 'mensual'
    impuesto TEXT,                      -- 'IRPF', 'IVA', 'IS'
    url_info TEXT,                      -- enlace a página AEAT del modelo
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE modelo_articulo (
    modelo_id INTEGER REFERENCES aeat_modelo(id) ON DELETE CASCADE,
    articulo_id INTEGER REFERENCES articulo(id) ON DELETE CASCADE,
    casilla TEXT,                       -- '0002', '0416', etc.
    nota TEXT,                          -- contexto breve de la relación
    fuente TEXT NOT NULL,               -- 'Instrucción Modelo 100 2025'
    url_fuente TEXT,                    -- URL directa a la fuente
    PRIMARY KEY (modelo_id, articulo_id)
);

-- Modelos AEAT v2: versionado por campaña, casillas, claves, instrucciones, normativa, formato
-- Aplicar tras 003_modelos_aeat.sql
-- Cada modelo puede tener múltiples campañas (2024, 2025, etc.) con casillas/claves/instrucciones distintas.

-- ---------------------------------------------------------------------------
-- 1. CAMPAÑAS — cada modelo puede tener N versiones por año/campaña
-- ---------------------------------------------------------------------------
CREATE TABLE modelo_campana (
    id              SERIAL PRIMARY KEY,
    modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
    campana         TEXT NOT NULL,              -- '2025', '2024', 'T1-2025', etc.
    version_form    TEXT,                       -- '1.0', '1.1' — versión del diseño
    url_instrucciones TEXT,                     -- PDF instrucciones AEAT
    url_normativa   TEXT,                       -- BOE/Orden que aprueba el modelo
    url_formato     TEXT,                       -- diseno de registro electronico
    activo          BOOLEAN NOT NULL DEFAULT true,  -- false = campaña obsoleta
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(modelo_id, campana)
);

CREATE INDEX IF NOT EXISTS idx_modelo_campana_modelo ON modelo_campana(modelo_id);

-- Enforce: only ONE active campaign per model at a time.
-- Postgres supports partial unique indexes for this exact pattern.
CREATE UNIQUE INDEX IF NOT EXISTS idx_modelo_campana_unique_active
    ON modelo_campana(modelo_id) WHERE activo = true;

-- ---------------------------------------------------------------------------
-- 2. CASILLAS — inventario completo de casillas por modelo/campaña
-- ---------------------------------------------------------------------------
CREATE TABLE modelo_casilla (
    id              SERIAL PRIMARY KEY,
    campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
    codigo          TEXT NOT NULL,              -- '0002', '0416', '01', etc.
    etiqueta        TEXT NOT NULL,              -- 'Rendimientos del trabajo'
    descripcion     TEXT,                       -- explicación breve
    tipo_casilla    TEXT,                       -- 'importe', 'checkbox', 'texto', 'numero', 'seccion'
    pagina          INTEGER,                    -- página del PDF donde aparece
    orden           INTEGER,                    -- orden de aparición en el modelo
    activa          BOOLEAN NOT NULL DEFAULT true,  -- false = casilla eliminada en esta campaña
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(campana_id, codigo)
);

CREATE INDEX IF NOT EXISTS idx_modelo_casilla_campana ON modelo_casilla(campana_id);

-- ---------------------------------------------------------------------------
-- 3. CLAVES — códigos de rendimiento/régimen/etc. por modelo/campaña
-- ---------------------------------------------------------------------------
CREATE TABLE modelo_clave (
    id              SERIAL PRIMARY KEY,
    campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
    codigo          TEXT NOT NULL,              -- '01', '02', 'A', 'B', etc.
    etiqueta        TEXT NOT NULL,              -- 'Rendimientos del trabajo'
    descripcion     TEXT,                       -- explicación de la clave
    tipo_clave      TEXT,                       -- 'rendimiento', 'regimen', 'tipo_retencion', etc.
    activa          BOOLEAN NOT NULL DEFAULT true,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(campana_id, codigo)
);

CREATE INDEX IF NOT EXISTS idx_modelo_clave_campana ON modelo_clave(campana_id);

-- ---------------------------------------------------------------------------
-- 4. INSTRUCCIONES — contenido paso a paso por modelo/campaña
-- ---------------------------------------------------------------------------
CREATE TABLE modelo_instruccion (
    id              SERIAL PRIMARY KEY,
    campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
    seccion         TEXT NOT NULL,              -- 'caracteristicas', 'quien-debe', 'como-rellenar', 'plazo'
    titulo          TEXT NOT NULL,
    contenido       TEXT NOT NULL,              -- Markdown/HTML del contenido
    orden           INTEGER DEFAULT 0,          -- orden de presentación
    creado_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_modelo_instruccion_campana ON modelo_instruccion(campana_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_modelo_instruccion_unique
    ON modelo_instruccion(campana_id, seccion, titulo);

-- ---------------------------------------------------------------------------
-- 5. NORMATIVA — órdenes BOE que regulan cada modelo (independiente de campaña)
-- ---------------------------------------------------------------------------
CREATE TABLE modelo_normativa (
    id              SERIAL PRIMARY KEY,
    modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
    boe_id          TEXT,                       -- 'BOE-A-2024-1772'
    titulo          TEXT NOT NULL,              -- 'Orden HAC/1234/2024'
    fecha           DATE,
    url_boe         TEXT,                       -- enlace al BOE
    resumen         TEXT,                       -- breve descripción
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(modelo_id, boe_id)
);

CREATE INDEX IF NOT EXISTS idx_modelo_normativa_modelo ON modelo_normativa(modelo_id);

-- ---------------------------------------------------------------------------
-- 6. FORMATO — especificaciones de diseño de registro por campaña
-- ---------------------------------------------------------------------------
CREATE TABLE modelo_campana_operativa (
    campana_id               INTEGER PRIMARY KEY REFERENCES modelo_campana(id) ON DELETE CASCADE,
    categoria_obligado       TEXT,
    frecuencia_presentacion  TEXT,
    ventana_presentacion     TEXT,
    canal_presentacion       TEXT,
    obligados_resumen        TEXT,
    plazo_resumen            TEXT,
    presentacion_resumen     TEXT,
    norma_base               TEXT,
    nota                     TEXT,
    origen_metadato          TEXT DEFAULT 'seed_curado',
    estado_metadato          TEXT DEFAULT 'curado',
    actualizado_at           TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE modelo_formato (
    id              SERIAL PRIMARY KEY,
    campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
    tipo_registro   TEXT NOT NULL,              -- 'declarante', 'perceptor', 'detalle'
    campos          JSONB,                      -- array de {nombre, tipo, longitud, posicion}
    url_diseno      TEXT,                       -- enlace al diseño de registro AEAT
    creado_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_modelo_formato_campana ON modelo_formato(campana_id);

-- ---------------------------------------------------------------------------
-- 7. VISTA: modelo_casilla_articulo — vincula casillas con artículos
-- ---------------------------------------------------------------------------
-- Esta vista junta modelo_casilla con modelo_articulo para que la API
-- pueda devolver casilla + artículo + normativa de un golpe.
-- La relación se hace via (modelo_id, casilla_codigo) cruzando con modelo_articulo.casilla.

-- ---------------------------------------------------------------------------
-- 8. CAMPAÑA ACTIVA POR DEFECTO
-- ---------------------------------------------------------------------------
-- Helper: función para obtener la campaña activa más reciente de un modelo
CREATE OR REPLACE FUNCTION modelo_campana_activa(p_modelo_id INTEGER)
RETURNS TABLE (
    id INTEGER,
    campana TEXT,
    url_instrucciones TEXT,
    url_normativa TEXT,
    url_formato TEXT
) AS $$
    SELECT id, campana, url_instrucciones, url_normativa, url_formato
    FROM modelo_campana
    WHERE modelo_id = p_modelo_id AND activo = true
    ORDER BY campana DESC
    LIMIT 1;
$$ LANGUAGE sql STABLE;

ALTER TABLE norma ADD COLUMN IF NOT EXISTS tipo_documento TEXT;
ALTER TABLE norma ADD COLUMN IF NOT EXISTS estado_cobertura TEXT;

UPDATE norma
SET tipo_documento = CASE codigo
    WHEN 'LGT' THEN 'ley'
    WHEN 'LIRPF' THEN 'ley'
    WHEN 'LIS' THEN 'ley'
    WHEN 'LIVA' THEN 'ley'
    ELSE 'ley'
END
WHERE tipo_documento IS NULL;

UPDATE norma
SET ambito = CASE
    WHEN ambito = 'fiscal' THEN 'tributario'
    ELSE ambito
END;

UPDATE norma
SET estado_cobertura = 'ingestada'
WHERE estado_cobertura IS NULL;

ALTER TABLE norma ALTER COLUMN tipo_documento SET NOT NULL;
ALTER TABLE norma ALTER COLUMN estado_cobertura SET NOT NULL;

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

-- 006_pgvector.sql — Vector embeddings for semantic search
-- Requires: pgvector extension (pgvector/pgvector:pg16 image)

CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding columns (384-dim for paraphrase-multilingual-MiniLM-L12-v2)
ALTER TABLE version_articulo
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- documento_fragmento may not exist yet (created by migration 0005)
-- Only add embedding if the table exists (post-migration)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documento_fragmento') THEN
        ALTER TABLE documento_fragmento ADD COLUMN IF NOT EXISTS embedding vector(384);
    END IF;
END $$;

ALTER TABLE documento_interpretativo
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- HNSW indexes for vector similarity search
-- m=16, ef_construction=64: good balance of build speed and query accuracy
CREATE INDEX IF NOT EXISTS idx_version_articulo_embedding
    ON version_articulo USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- documento_fragmento index (only if table+column exist)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documento_fragmento' AND column_name = 'embedding'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_documento_fragmento_embedding
            ON documento_fragmento USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_documento_interpretativo_embedding
    ON documento_interpretativo USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

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

-- IRPF brackets, personal minimums, work income reductions
-- Data source: Ley 35/2006 (LIRPF)

CREATE TABLE irpf_brackets (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    bracket_type    TEXT NOT NULL,                    -- 'general', 'savings'
    territory       TEXT NOT NULL DEFAULT 'state',    -- 'state', or CCAA code
    from_amount     NUMERIC(12,2) NOT NULL,
    to_amount       NUMERIC(12,2),                    -- NULL = no upper limit
    rate            NUMERIC(5,2) NOT NULL,            -- percentage
    source          TEXT,
    source_url      TEXT,
    ingestion_timestamp TIMESTAMPTZ DEFAULT now(),
    superseded      INTEGER NOT NULL DEFAULT 0,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, bracket_type, territory, from_amount, to_amount)
);

CREATE TABLE irpf_personal_minimums (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    category        TEXT NOT NULL,                    -- 'taxpayer', 'descendants', 'ascendants', 'disability'
    subcategory     TEXT NOT NULL,                    -- 'general', 'age_65_plus', 'first', '33_to_65_percent', etc.
    amount          NUMERIC(12,2) NOT NULL,
    source          TEXT,
    source_url      TEXT,
    ingestion_timestamp TIMESTAMPTZ DEFAULT now(),
    superseded      INTEGER NOT NULL DEFAULT 0,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, category, subcategory)
);

CREATE TABLE irpf_work_income_reduction (
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
    source_url      TEXT,
    ingestion_timestamp TIMESTAMPTZ DEFAULT now(),
    superseded      INTEGER NOT NULL DEFAULT 0,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, rule_type)
);

CREATE INDEX IF NOT EXISTS idx_irpf_brackets_year ON irpf_brackets(year);
CREATE INDEX IF NOT EXISTS idx_irpf_personal_minimums_year ON irpf_personal_minimums(year);
CREATE INDEX IF NOT EXISTS idx_irpf_work_income_reduction_year ON irpf_work_income_reduction(year);

-- Social Security rates — contribution bases and rates
-- Data source: Seguridad Social / REI

CREATE TABLE ss_rates (
    id              SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    category        TEXT NOT NULL,                    -- 'general', 'young', 'trainees', 'freelance'
    base_monthly    NUMERIC(12,2),                    -- monthly contribution base
    base_annual     NUMERIC(12,2),                    -- annual contribution base
    rate_common     NUMERIC(5,2),                     -- common contribution rate %
    rate_accident   NUMERIC(5,2),                     -- accident insurance rate % (varies by risk category)
    total_rate      NUMERIC(5,2),                     -- combined rate %
    source          TEXT,
    source_url      TEXT,
    ingestion_timestamp TIMESTAMPTZ DEFAULT now(),
    superseded      INTEGER NOT NULL DEFAULT 0,
    creado_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(year, category)
);

CREATE INDEX IF NOT EXISTS idx_ss_rates_year ON ss_rates(year);

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
