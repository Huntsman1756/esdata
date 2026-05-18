BEGIN;

ALTER TABLE norma ADD COLUMN IF NOT EXISTS norma_padre_celex TEXT;

INSERT INTO norma (
    codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
    tipo_documento, ambito, estado_cobertura, vigente_desde,
    celex, tipo_norma, publicacion_doue, url_eurlex, vigente,
    derogada_por, norma_padre_celex
) VALUES
(
    '32017R0587',
    'Reglamento Delegado (UE) 2017/587 normas tecnicas de regulacion sobre transparencia para instrumentos de renta variable',
    'EUR-CELEX-32017R0587',
    'http://data.europa.eu/eli/reg_del/2017/587/oj',
    'ue',
    'eurlex',
    'rts',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2017-03-31',
    '32017R0587',
    'reglamento_delegado_ue',
    DATE '2017-03-31',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0587',
    TRUE,
    NULL,
    '32014R0600'
),
(
    '32017R0583',
    'Reglamento Delegado (UE) 2017/583 normas tecnicas de regulacion sobre transparencia para instrumentos distintos de los de renta variable',
    'EUR-CELEX-32017R0583',
    'http://data.europa.eu/eli/reg_del/2017/583/oj',
    'ue',
    'eurlex',
    'rts',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2017-03-31',
    '32017R0583',
    'reglamento_delegado_ue',
    DATE '2017-03-31',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0583',
    TRUE,
    NULL,
    '32014R0600'
)
ON CONFLICT (codigo) DO UPDATE SET
    titulo = EXCLUDED.titulo,
    boe_id = EXCLUDED.boe_id,
    eli_uri = EXCLUDED.eli_uri,
    jurisdiccion = EXCLUDED.jurisdiccion,
    tipo_fuente = EXCLUDED.tipo_fuente,
    tipo_documento = EXCLUDED.tipo_documento,
    ambito = EXCLUDED.ambito,
    estado_cobertura = EXCLUDED.estado_cobertura,
    vigente_desde = EXCLUDED.vigente_desde,
    celex = EXCLUDED.celex,
    tipo_norma = EXCLUDED.tipo_norma,
    publicacion_doue = EXCLUDED.publicacion_doue,
    url_eurlex = EXCLUDED.url_eurlex,
    vigente = EXCLUDED.vigente,
    derogada_por = EXCLUDED.derogada_por,
    norma_padre_celex = EXCLUDED.norma_padre_celex;

COMMIT;
