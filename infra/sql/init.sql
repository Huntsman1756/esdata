CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS norma (
    id SERIAL PRIMARY KEY,
    codigo TEXT UNIQUE NOT NULL,
    titulo TEXT NOT NULL,
    boe_id TEXT UNIQUE NOT NULL,
    eli_uri TEXT UNIQUE,
    jurisdiccion TEXT NOT NULL,
    tipo_fuente TEXT NOT NULL,
    ambito TEXT NOT NULL,
    vigente_desde DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS articulo (
    id SERIAL PRIMARY KEY,
    norma_id INTEGER NOT NULL REFERENCES norma(id),
    numero TEXT NOT NULL,
    titulo TEXT,
    tipo TEXT NOT NULL,
    UNIQUE (norma_id, numero)
);

CREATE TABLE IF NOT EXISTS version_articulo (
    id SERIAL PRIMARY KEY,
    articulo_id INTEGER NOT NULL REFERENCES articulo(id),
    texto TEXT NOT NULL,
    vigente_desde DATE NOT NULL,
    vigente_hasta DATE,
    boe_bloque_id TEXT
);

CREATE TABLE IF NOT EXISTS documento_interpretativo (
    id SERIAL PRIMARY KEY,
    tipo_documento TEXT NOT NULL,
    organismo_emisor TEXT NOT NULL,
    jurisdiccion TEXT NOT NULL,
    tipo_fuente TEXT NOT NULL,
    ambito TEXT NOT NULL,
    referencia TEXT UNIQUE NOT NULL,
    fecha DATE NOT NULL,
    titulo TEXT,
    texto TEXT NOT NULL,
    url_fuente TEXT
);

CREATE TABLE IF NOT EXISTS documento_articulo (
    documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
    articulo_id INTEGER NOT NULL REFERENCES articulo(id),
    metodo_enlace TEXT NOT NULL,
    confianza_enlace NUMERIC(3,2) NOT NULL,
    nota TEXT,
    PRIMARY KEY (documento_id, articulo_id)
);

CREATE TABLE IF NOT EXISTS materia (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    etiqueta TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS articulo_materia (
    articulo_id INTEGER NOT NULL REFERENCES articulo(id),
    materia_id INTEGER NOT NULL REFERENCES materia(id),
    relevancia SMALLINT NOT NULL DEFAULT 1,
    PRIMARY KEY (articulo_id, materia_id)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id SERIAL PRIMARY KEY,
    worker TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    items_processed INTEGER,
    error_msg TEXT
);

-- Seed mínimo: solo normas, materias y doctrina.
-- Los artículos y versiones los ingesta el worker BOE en tiempo de ejecución.
-- En desarrollo local, el worker rellena articulo y version_articulo tras arrancar.

-- Normas (metadatos de referencia)
INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde)
VALUES
    ('LIVA', 'Ley del Impuesto sobre el Valor Anadido', 'BOE-A-1992-28740', 'https://www.boe.es/eli/es/l/1992/12/28/37', 'es', 'boe', 'fiscal', '1993-01-01'),
    ('LIRPF', 'Ley del Impuesto sobre la Renta de las Personas Físicas', 'BOE-A-2006-20764', 'https://www.boe.es/eli/es/l/2006/11/23/35', 'es', 'boe', 'fiscal', '2007-01-01'),
    ('LIS', 'Ley del Impuesto sobre Sociedades', 'BOE-A-2014-12328', 'https://www.boe.es/eli/es/l/2014/11/27/27', 'es', 'boe', 'fiscal', '2015-01-01'),
    ('LGT', 'Ley General Tributaria', 'BOE-A-2003-23186', 'https://www.boe.es/eli/es/l/2003/12/17/58', 'es', 'boe', 'fiscal', '2004-01-01')
ON CONFLICT (codigo) DO NOTHING;

-- Materias (taxonomía curada — no las genera el worker)
INSERT INTO materia (slug, etiqueta)
VALUES ('tipo-reducido-iva', 'Tipo reducido IVA')
ON CONFLICT (slug) DO NOTHING;

-- Doctrina interpretativa de referencia (seed local para desarrollo)
INSERT INTO documento_interpretativo (
    tipo_documento,
    organismo_emisor,
    jurisdiccion,
    tipo_fuente,
    ambito,
    referencia,
    fecha,
    titulo,
    texto,
    url_fuente
)
VALUES (
    'consulta_vinculante',
    'DGT',
    'es',
    'dgt',
    'fiscal',
    'V0000-26',
    '2026-01-15',
    'Consulta DGT sobre tipo reducido',
    'Documento de referencia para desarrollo local.',
    'https://example.invalid/dgt/V0000-26'
)
ON CONFLICT (referencia) DO NOTHING;

-- Los enlaces articulo<->materia y documento<->articulo se crean
-- tras la ingesta del worker, cuando los artículos existen en BD.
