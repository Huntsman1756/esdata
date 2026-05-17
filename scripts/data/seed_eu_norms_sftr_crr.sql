BEGIN;

-- Normalize previous EUR-Lex ingestions to canonical CELEX codigo values.
UPDATE norma
SET codigo = '32019R0876'
WHERE boe_id = 'EUR-CELEX-32019R0876'
  AND codigo <> '32019R0876'
  AND NOT EXISTS (SELECT 1 FROM norma existing WHERE existing.codigo = '32019R0876');

INSERT INTO norma (
    codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
    tipo_documento, ambito, estado_cobertura, vigente_desde,
    celex, tipo_norma, publicacion_doue, url_eurlex, vigente, derogada_por
) VALUES
(
    '32015R2365',
    'Reglamento (UE) 2015/2365 sobre transparencia de las operaciones de financiacion de valores y de reutilizacion (SFTR)',
    'EUR-CELEX-32015R2365',
    'http://data.europa.eu/eli/reg/2015/2365/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2015-11-25',
    '32015R2365',
    'reglamento_ue',
    DATE '2015-12-23',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015R2365',
    TRUE,
    NULL
),
(
    '32013R0575',
    'Reglamento (UE) n. 575/2013 sobre requisitos prudenciales de las entidades de credito y las empresas de inversion (CRR)',
    'EUR-CELEX-32013R0575',
    'http://data.europa.eu/eli/reg/2013/575/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2013-06-26',
    '32013R0575',
    'reglamento_ue',
    DATE '2013-06-27',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0575',
    TRUE,
    NULL
),
(
    '32019R0876',
    'Reglamento (UE) 2019/876 por el que se modifica el CRR (CRR2)',
    'EUR-CELEX-32019R0876',
    'http://data.europa.eu/eli/reg/2019/876/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2019-05-20',
    '32019R0876',
    'reglamento_ue',
    DATE '2019-06-07',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32019R0876',
    TRUE,
    NULL
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
    derogada_por = EXCLUDED.derogada_por;

UPDATE obligacion_perfil
SET norma_codigo = '32013R0575',
    source_url = 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0575',
    notas = CONCAT_WS(
        ' ',
        NULLIF(notas, ''),
        'Sprint D: referencia CRR normalizada a CELEX 32013R0575; articulo pendiente de precision antes de verificar.'
    )
WHERE descripcion ILIKE '%prudencial%recursos propios%'
  AND perfil_codigo IN ('sociedad_valores', 'agencia_valores');

WITH inserted AS (
    INSERT INTO obligacion_perfil (
        perfil_codigo, obligacion_tipo, descripcion,
        periodicidad, plazo_descripcion, modelo_aeat,
        norma_codigo, articulo_referencia, fuente_secundaria,
        evidencia_tipo, safe_to_answer, verified, completeness,
        source_url, capture_date, notas
    )
    VALUES (
        'sociedad_valores',
        'REPORTING',
        'Reporte SFTR - operaciones de financiacion de valores',
        'diaria',
        'T+1 para comunicacion a registro de operaciones cuando aplica',
        NULL,
        '32015R2365',
        'art. 4',
        NULL,
        'reglamento_ue',
        TRUE,
        TRUE,
        'parcial',
        'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015R2365',
        CURRENT_DATE,
        'Aplicabilidad condicional: solo si realiza SFT, como repos, prestamo de valores o buy-sell back.'
    )
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion)
    DO UPDATE SET
        periodicidad = EXCLUDED.periodicidad,
        plazo_descripcion = EXCLUDED.plazo_descripcion,
        norma_codigo = EXCLUDED.norma_codigo,
        articulo_referencia = EXCLUDED.articulo_referencia,
        evidencia_tipo = EXCLUDED.evidencia_tipo,
        verified = EXCLUDED.verified,
        completeness = EXCLUDED.completeness,
        source_url = EXCLUDED.source_url,
        capture_date = EXCLUDED.capture_date,
        notas = EXCLUDED.notas
    RETURNING id
)
INSERT INTO obligacion_fuente (
    obligacion_id, fuente_tipo, codigo_referencia, articulo,
    descripcion, source_url, peso
)
SELECT inserted.id,
       'reglamento_ue',
       '32015R2365',
       'art. 4',
       'SFTR reporting obligation for securities financing transactions',
       'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015R2365',
       1
FROM inserted
WHERE NOT EXISTS (
    SELECT 1
    FROM obligacion_fuente existing
    WHERE existing.obligacion_id = inserted.id
      AND existing.codigo_referencia = '32015R2365'
      AND existing.articulo = 'art. 4'
);

COMMIT;
