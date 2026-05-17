-- Sprint E seed: missing norms for complete applicability profiles.
-- Official-source corrections:
--   LEY10_2014 uses BOE-A-2014-6726, not BOE-A-2014-6435.
--   RD19_2018 uses BOE-A-2018-16036, not BOE-A-2018-16673.
-- Safe to rerun: rows are upserted by norma.codigo.

BEGIN;

INSERT INTO norma (
    codigo,
    titulo,
    boe_id,
    eli_uri,
    jurisdiccion,
    tipo_fuente,
    tipo_documento,
    ambito,
    estado_cobertura,
    vigente_desde,
    celex,
    tipo_norma,
    publicacion_doue,
    url_eurlex,
    vigente
) VALUES
(
    '32015L2366',
    'Directiva (UE) 2015/2366 sobre servicios de pago en el mercado interior (PSD2)',
    'CELEX-32015L2366',
    'http://data.europa.eu/eli/dir/2015/2366/oj',
    'UE',
    'eurlex',
    'directiva_ue',
    'servicios_pago',
    'metadata_only',
    DATE '2015-12-23',
    '32015L2366',
    'directiva_ue',
    DATE '2015-12-23',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015L2366',
    true
),
(
    'LEY10_2014',
    'Ley 10/2014, de ordenacion, supervision y solvencia de entidades de credito',
    'BOE-A-2014-6726',
    'https://www.boe.es/eli/es/l/2014/06/26/10/con',
    'ES',
    'boe',
    'ley_nacional',
    'entidades_credito',
    'metadata_only',
    DATE '2014-06-28',
    NULL,
    'ley_nacional',
    NULL,
    NULL,
    true
),
(
    'RD19_2018',
    'Real Decreto-ley 19/2018, de servicios de pago y otras medidas urgentes en materia financiera',
    'BOE-A-2018-16036',
    'https://www.boe.es/eli/es/rdl/2018/11/23/19/con',
    'ES',
    'boe',
    'rd_ley_nacional',
    'servicios_pago',
    'metadata_only',
    DATE '2018-11-25',
    NULL,
    'rd_ley_nacional',
    NULL,
    NULL,
    true
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
    vigente = EXCLUDED.vigente;

COMMIT;
