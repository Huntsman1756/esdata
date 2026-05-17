BEGIN;

-- Normalize previous EUR-Lex ingestion to the canonical CELEX codigo.
UPDATE norma
SET codigo = '32012R0648'
WHERE boe_id = 'EUR-CELEX-32012R0648'
  AND codigo <> '32012R0648'
  AND NOT EXISTS (SELECT 1 FROM norma existing WHERE existing.codigo = '32012R0648');

INSERT INTO norma (
    codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
    tipo_documento, ambito, estado_cobertura, vigente_desde,
    celex, tipo_norma, publicacion_doue, url_eurlex, vigente, derogada_por
) VALUES
(
    '32012R0648',
    'Reglamento (UE) n. 648/2012 relativo a los derivados OTC, las entidades de contrapartida central y los registros de operaciones (EMIR)',
    'EUR-CELEX-32012R0648',
    'http://data.europa.eu/eli/reg/2012/648/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2012-07-04',
    '32012R0648',
    'reglamento_ue',
    DATE '2012-07-04',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32012R0648',
    TRUE,
    NULL
),
(
    '32019R0834',
    'Reglamento (UE) 2019/834 por el que se modifica EMIR (EMIR Refit)',
    'EUR-CELEX-32019R0834',
    'http://data.europa.eu/eli/reg/2019/834/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2019-05-20',
    '32019R0834',
    'reglamento_ue',
    DATE '2019-05-28',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32019R0834',
    TRUE,
    NULL
),
(
    '32022R2554',
    'Reglamento (UE) 2022/2554 sobre la resiliencia operativa digital del sector financiero (DORA)',
    'EUR-CELEX-32022R2554',
    'http://data.europa.eu/eli/reg/2022/2554/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2022-12-14',
    '32022R2554',
    'reglamento_ue',
    DATE '2022-12-27',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554',
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
        'CONTROL_INTERNO',
        'Marco de gestion del riesgo TIC (DORA)',
        'continua',
        NULL,
        NULL,
        '32022R2554',
        'art. 5-16',
        NULL,
        'reglamento_ue',
        TRUE,
        TRUE,
        'completa',
        'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554',
        CURRENT_DATE,
        'Obligacion de marco de gestion del riesgo TIC verificada contra DORA arts. 5 a 16.'
    )
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion)
    DO UPDATE SET
        periodicidad = EXCLUDED.periodicidad,
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
       '32022R2554',
       'art. 5-16',
       'DORA ICT risk management framework',
       'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554',
       1
FROM inserted
WHERE NOT EXISTS (
    SELECT 1
    FROM obligacion_fuente existing
    WHERE existing.obligacion_id = inserted.id
      AND existing.codigo_referencia = '32022R2554'
      AND existing.articulo = 'art. 5-16'
);

COMMIT;
