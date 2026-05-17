BEGIN;

-- Previous EUR-Lex ingestions used internal codes for these two acts while
-- preserving the official CELEX in boe_id. Sprint D makes CELEX the canonical
-- codigo for EU norms, so normalize before the idempotent upsert.
UPDATE norma
SET codigo = '32014L0065'
WHERE boe_id = 'EUR-CELEX-32014L0065'
  AND codigo <> '32014L0065'
  AND NOT EXISTS (SELECT 1 FROM norma existing WHERE existing.codigo = '32014L0065');

UPDATE norma
SET codigo = '32014R0600'
WHERE boe_id = 'EUR-CELEX-32014R0600'
  AND codigo <> '32014R0600'
  AND NOT EXISTS (SELECT 1 FROM norma existing WHERE existing.codigo = '32014R0600');

INSERT INTO norma (
    codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
    tipo_documento, ambito, estado_cobertura, vigente_desde,
    celex, tipo_norma, publicacion_doue, url_eurlex, vigente, derogada_por
) VALUES
(
    '32014L0065',
    'Directiva 2014/65/UE relativa a los mercados de instrumentos financieros (MiFID II)',
    'EUR-CELEX-32014L0065',
    'http://data.europa.eu/eli/dir/2014/65/oj',
    'ue',
    'eurlex',
    'directiva_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2014-06-12',
    '32014L0065',
    'directiva_ue',
    DATE '2014-06-12',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065',
    TRUE,
    NULL
),
(
    '32014R0600',
    'Reglamento (UE) n.º 600/2014 relativo a los mercados de instrumentos financieros (MiFIR)',
    'EUR-CELEX-32014R0600',
    'http://data.europa.eu/eli/reg/2014/600/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2014-06-12',
    '32014R0600',
    'reglamento_ue',
    DATE '2014-06-12',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600',
    TRUE,
    NULL
),
(
    '32017R0571',
    'Reglamento Delegado (UE) 2017/571 sobre servicios de suministro de datos conforme a MiFID II',
    'EUR-CELEX-32017R0571',
    'http://data.europa.eu/eli/reg_del/2017/571/oj',
    'ue',
    'eurlex',
    'rts',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2017-03-31',
    '32017R0571',
    'rts',
    DATE '2017-03-31',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0571',
    TRUE,
    NULL
),
(
    '32017R0590',
    'Reglamento Delegado (UE) 2017/590 — RTS 22 sobre comunicación de operaciones a autoridades competentes',
    'EUR-CELEX-32017R0590',
    'http://data.europa.eu/eli/reg_del/2017/590/oj',
    'ue',
    'eurlex',
    'rts',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2017-03-31',
    '32017R0590',
    'rts',
    DATE '2017-03-31',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0590',
    TRUE,
    NULL
),
(
    '32017R0565',
    'Reglamento Delegado (UE) 2017/565 por el que se completa MiFID II en requisitos organizativos y condiciones de funcionamiento',
    'EUR-CELEX-32017R0565',
    'http://data.europa.eu/eli/reg_del/2017/565/oj',
    'ue',
    'eurlex',
    'rts',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2017-03-31',
    '32017R0565',
    'rts',
    DATE '2017-03-31',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0565',
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
SET norma_codigo = '32014R0600',
    articulo_referencia = 'art. 26',
    verified = TRUE,
    completeness = 'completa',
    source_url = 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600',
    notas = CONCAT_WS(
        ' ',
        NULLIF(notas, ''),
        'Verificado en Sprint D contra MiFIR art. 26 y RTS 22 CELEX 32017R0590.'
    )
WHERE descripcion ILIKE '%MiFIR%transaction reporting%'
  AND perfil_codigo IN ('sociedad_valores', 'agencia_valores');

INSERT INTO obligacion_fuente (
    obligacion_id, fuente_tipo, codigo_referencia, articulo,
    descripcion, source_url, peso
)
SELECT op.id,
       'reglamento_ue',
       '32014R0600',
       'art. 26',
       'MiFIR transaction reporting',
       'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600',
       1
FROM obligacion_perfil op
WHERE op.descripcion ILIKE '%MiFIR%transaction reporting%'
  AND op.perfil_codigo IN ('sociedad_valores', 'agencia_valores')
  AND NOT EXISTS (
      SELECT 1
      FROM obligacion_fuente existing
      WHERE existing.obligacion_id = op.id
        AND existing.codigo_referencia = '32014R0600'
        AND existing.articulo = 'art. 26'
  );

INSERT INTO obligacion_fuente (
    obligacion_id, fuente_tipo, codigo_referencia, articulo,
    descripcion, source_url, peso
)
SELECT op.id,
       'rts',
       '32017R0590',
       NULL,
       'RTS 22 transaction reporting technical standards',
       'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0590',
       2
FROM obligacion_perfil op
WHERE op.descripcion ILIKE '%MiFIR%transaction reporting%'
  AND op.perfil_codigo IN ('sociedad_valores', 'agencia_valores')
  AND NOT EXISTS (
      SELECT 1
      FROM obligacion_fuente existing
      WHERE existing.obligacion_id = op.id
        AND existing.codigo_referencia = '32017R0590'
  );

COMMIT;
