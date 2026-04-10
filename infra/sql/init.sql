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

-- Seed mínimo para desarrollo local.
-- Solo LIVA 91 tiene texto seed; las demás normas se ingestan vía worker BOE.
-- En producción el worker BOE reemplaza el texto seed con datos reales.

-- Normas
INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde)
VALUES
    ('LIVA', 'Ley del Impuesto sobre el Valor Anadido', 'BOE-A-1992-28740', 'https://www.boe.es/eli/es/l/1992/12/28/37', 'es', 'boe', 'fiscal', '1993-01-01'),
    ('LIRPF', 'Ley del Impuesto sobre la Renta de las Personas Físicas', 'BOE-A-2006-20764', 'https://www.boe.es/eli/es/l/2006/11/23/35', 'es', 'boe', 'fiscal', '2007-01-01'),
    ('LIS', 'Ley del Impuesto sobre Sociedades', 'BOE-A-2014-12328', 'https://www.boe.es/eli/es/l/2014/11/27/27', 'es', 'boe', 'fiscal', '2015-01-01'),
    ('LGT', 'Ley General Tributaria', 'BOE-A-2003-23186', 'https://www.boe.es/eli/es/l/2003/12/17/58', 'es', 'boe', 'fiscal', '2004-01-01')
ON CONFLICT (codigo) DO NOTHING;

-- LIVA 91: placeholder mínimo para desarrollo y tests.
-- El worker BOE reemplaza el texto con datos reales al hacer sync.
INSERT INTO articulo (norma_id, numero, titulo, tipo)
SELECT id, '91', 'Tipos reducidos', 'articulo'
FROM norma
WHERE codigo = 'LIVA'
ON CONFLICT (norma_id, numero) DO NOTHING;

INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
SELECT a.id, 'Texto seed del articulo 91 de la LIVA para entorno local con referencia a tipo reducido.', '1993-01-01', NULL, 'seed-liva-91'
FROM articulo a
JOIN norma n ON n.id = a.norma_id
WHERE n.codigo = 'LIVA'
  AND a.numero = '91'
  AND NOT EXISTS (
      SELECT 1
      FROM version_articulo va
      WHERE va.articulo_id = a.id
        AND va.vigente_desde = DATE '1993-01-01'
  );

-- Materias, doctrina y enlaces seed (solo para tests locales)
INSERT INTO materia (slug, etiqueta)
VALUES ('tipo-reducido-iva', 'Tipo reducido IVA')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO articulo_materia (articulo_id, materia_id, relevancia)
SELECT a.id, m.id, 3
FROM articulo a
JOIN norma n ON n.id = a.norma_id
JOIN materia m ON m.slug = 'tipo-reducido-iva'
WHERE n.codigo = 'LIVA' AND a.numero = '91'
ON CONFLICT (articulo_id, materia_id) DO NOTHING;

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
    'Seed DGT',
    'Documento interpretativo seed relacionado con LIVA 91.',
    'https://example.invalid/dgt/V0000-26'
)
ON CONFLICT (referencia) DO NOTHING;

INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
SELECT d.id, a.id, 'manual', 1.00, 'Seed local'
FROM documento_interpretativo d
JOIN articulo a ON a.numero = '91'
JOIN norma n ON n.id = a.norma_id
WHERE d.referencia = 'V0000-26'
  AND n.codigo = 'LIVA'
ON CONFLICT (documento_id, articulo_id) DO NOTHING;
