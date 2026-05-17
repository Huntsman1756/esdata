BEGIN;

-- Normalize previous EUR-Lex ingestions to canonical CELEX codigo values.
UPDATE norma
SET codigo = '32009L0065'
WHERE boe_id = 'EUR-CELEX-32009L0065'
  AND codigo <> '32009L0065'
  AND NOT EXISTS (SELECT 1 FROM norma existing WHERE existing.codigo = '32009L0065');

UPDATE norma
SET codigo = '32011L0061'
WHERE boe_id = 'EUR-CELEX-32011L0061'
  AND codigo <> '32011L0061'
  AND NOT EXISTS (SELECT 1 FROM norma existing WHERE existing.codigo = '32011L0061');

INSERT INTO norma (
    codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
    tipo_documento, ambito, estado_cobertura, vigente_desde,
    celex, tipo_norma, publicacion_doue, url_eurlex, vigente, derogada_por
) VALUES
(
    '32009L0065',
    'Directiva 2009/65/CE sobre organismos de inversion colectiva en valores mobiliarios (UCITS IV)',
    'EUR-CELEX-32009L0065',
    'http://data.europa.eu/eli/dir/2009/65/oj',
    'ue',
    'eurlex',
    'directiva_ue',
    'gestion_activos_ue',
    'metadata_official',
    DATE '2009-07-13',
    '32009L0065',
    'directiva_ue',
    DATE '2009-11-17',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32009L0065',
    TRUE,
    NULL
),
(
    '32011L0061',
    'Directiva 2011/61/UE relativa a los gestores de fondos de inversion alternativos (AIFMD)',
    'EUR-CELEX-32011L0061',
    'http://data.europa.eu/eli/dir/2011/61/oj',
    'ue',
    'eurlex',
    'directiva_ue',
    'gestion_activos_ue',
    'metadata_official',
    DATE '2011-06-08',
    '32011L0061',
    'directiva_ue',
    DATE '2011-07-01',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32011L0061',
    TRUE,
    NULL
),
(
    '32013R0231',
    'Reglamento Delegado (UE) n. 231/2013 que complementa la AIFMD',
    'EUR-CELEX-32013R0231',
    'http://data.europa.eu/eli/reg_del/2013/231/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'gestion_activos_ue',
    'metadata_official',
    DATE '2012-12-19',
    '32013R0231',
    'reglamento_ue',
    DATE '2013-03-22',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0231',
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

WITH upserted AS (
    INSERT INTO obligacion_perfil (
        perfil_codigo, obligacion_tipo, descripcion,
        periodicidad, plazo_descripcion, modelo_aeat,
        norma_codigo, articulo_referencia, fuente_secundaria,
        evidencia_tipo, safe_to_answer, verified, completeness,
        source_url, capture_date, notas
    )
    VALUES
    (
        'sgiic',
        'REPORTING',
        'Reporte a CNMV - activos bajo gestion IIC (AIFMD Annex IV)',
        'trimestral',
        'Periodicidad variable segun AUM y tipo de fondo',
        NULL,
        '32011L0061',
        'Annex IV',
        NULL,
        'directiva_ue',
        TRUE,
        FALSE,
        'parcial',
        'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32011L0061',
        CURRENT_DATE,
        'Obligacion condicional para AIFM/SGIIC; requiere concretar regimen CNMV y AUM antes de verificar.'
    ),
    (
        'sgiic',
        'CONTROL_INTERNO',
        'Politica de gestion de liquidez IIC',
        'continua',
        'Revision anual y cuando cambie el perfil de liquidez',
        NULL,
        '32011L0061',
        'art. 16',
        'ESMA70-156-4717',
        'directiva_ue',
        TRUE,
        TRUE,
        'completa',
        'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32011L0061',
        CURRENT_DATE,
        'Gestion de liquidez verificada contra AIFMD art. 16; guia ESMA pendiente de carga como fuente secundaria.'
    ),
    (
        'sgiic',
        'REPORTING',
        'Reporte estres de liquidez IIC',
        'ad_hoc',
        'Cuando ESMA o CNMV lo requiera',
        NULL,
        '32011L0061',
        'art. 16',
        'ESMA34-671404336-1364',
        'guideline_esma',
        TRUE,
        FALSE,
        'parcial',
        'https://www.esma.europa.eu/sites/default/files/2026-03/ESMA34-671404336-1364_Guidelines_on_liquidity_management_tools_of_UCITS_and_AIFs.pdf',
        CURRENT_DATE,
        'Obligacion operativa vinculada a herramientas de gestion de liquidez; fuente ESMA 2026 pendiente de carga como guideline.'
    )
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion)
    DO UPDATE SET
        periodicidad = EXCLUDED.periodicidad,
        plazo_descripcion = EXCLUDED.plazo_descripcion,
        norma_codigo = EXCLUDED.norma_codigo,
        articulo_referencia = EXCLUDED.articulo_referencia,
        fuente_secundaria = EXCLUDED.fuente_secundaria,
        evidencia_tipo = EXCLUDED.evidencia_tipo,
        verified = EXCLUDED.verified,
        completeness = EXCLUDED.completeness,
        source_url = EXCLUDED.source_url,
        capture_date = EXCLUDED.capture_date,
        notas = EXCLUDED.notas
    RETURNING id, descripcion, norma_codigo, articulo_referencia, source_url
)
INSERT INTO obligacion_fuente (
    obligacion_id, fuente_tipo, codigo_referencia, articulo,
    descripcion, source_url, peso
)
SELECT upserted.id,
       CASE
           WHEN upserted.descripcion ILIKE '%estres de liquidez%' THEN 'guideline_esma'
           ELSE 'directiva_ue'
       END,
       upserted.norma_codigo,
       upserted.articulo_referencia,
       upserted.descripcion,
       upserted.source_url,
       1
FROM upserted
WHERE NOT EXISTS (
    SELECT 1
    FROM obligacion_fuente existing
    WHERE existing.obligacion_id = upserted.id
      AND existing.codigo_referencia = upserted.norma_codigo
      AND COALESCE(existing.articulo, '') = COALESCE(upserted.articulo_referencia, '')
);

COMMIT;
