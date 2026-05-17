BEGIN;

INSERT INTO documento_interpretativo (
    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
    ambito, referencia, fecha, titulo, texto, url_fuente,
    fecha_publicacion, estado_vigencia, ambito_tematico,
    regulacion_relacionada, row_completeness, row_provenance, metadata
) VALUES
(
    'guideline_esma',
    'ESMA',
    'ue',
    'esma',
    'MiFIR transaction reporting art. 26',
    'ESMA50-165-2535',
    DATE '2017-10-10',
    'Q&A on MiFIR data reporting',
    'ESMA Q&A and guidance page for MiFIR data reporting, including transaction reporting under MiFIR art. 26 and related technical standards.',
    'https://www.esma.europa.eu/document/qas-mifir-data-reporting',
    '2017-10-10',
    'vigente',
    'mifir_reporting',
    '32014R0600;32017R0590',
    'parcial',
    'official_esma_metadata',
    jsonb_build_object(
        'source_url', 'https://www.esma.europa.eu/document/qas-mifir-data-reporting',
        'sujeto_obligado', 'esi',
        'contract', 'guideline_esma',
        'verified_source', true
    )
),
(
    'guideline_esma',
    'ESMA',
    'ue',
    'esma',
    'UCITS AIFMD liquidity stress testing',
    'ESMA34-39-897',
    DATE '2020-07-16',
    'Guidelines on liquidity stress testing in UCITS and AIFs',
    'ESMA guidelines on liquidity stress testing in UCITS and AIFs. Supervisory guidance, not primary law.',
    'https://www.esma.europa.eu/document/guidelines-liquidity-stress-testing-in-ucits-and-aifs',
    '2020-07-16',
    'vigente',
    'fund_liquidity',
    '32009L0065;32011L0061',
    'parcial',
    'official_esma_metadata',
    jsonb_build_object(
        'source_url', 'https://www.esma.europa.eu/document/guidelines-liquidity-stress-testing-in-ucits-and-aifs',
        'sujeto_obligado', 'sgiic',
        'contract', 'guideline_esma',
        'verified_source', true,
        'note', 'Official ESMA reference is ESMA34-39-897.'
    )
),
(
    'guideline_esma',
    'ESMA',
    'ue',
    'esma',
    'UCITS AIFMD liquidity management tools',
    'ESMA34-671404336-1364',
    DATE '2026-03-12',
    'Guidelines on liquidity management tools of UCITS and open-ended AIFs',
    'ESMA guidelines on selection and calibration of liquidity management tools for UCITS and open-ended AIFs. Supervisory guidance, not primary law.',
    'https://www.esma.europa.eu/document/guidelines-liquidity-management-tools-ucits-and-open-ended-aifs',
    '2026-03-12',
    'vigente',
    'fund_liquidity',
    '32009L0065;32011L0061',
    'parcial',
    'official_esma_metadata',
    jsonb_build_object(
        'source_url', 'https://www.esma.europa.eu/document/guidelines-liquidity-management-tools-ucits-and-open-ended-aifs',
        'pdf_url', 'https://www.esma.europa.eu/sites/default/files/2026-03/ESMA34-671404336-1364_Guidelines_on_liquidity_management_tools_of_UCITS_and_open-ended_AIFs.pdf',
        'sujeto_obligado', 'sgiic',
        'contract', 'guideline_esma',
        'verified_source', true
    )
),
(
    'guideline_esma',
    'ESMA',
    'ue',
    'esma',
    'MiFID II product governance target market',
    'ESMA35-43-3448',
    DATE '2023-03-27',
    'Guidelines on MiFID II product governance requirements',
    'ESMA guidelines on MiFID II product governance requirements. Supervisory guidance, not primary law.',
    'https://www.esma.europa.eu/document/guidelines-mifid-ii-product-governance-requirements-0',
    '2023-03-27',
    'vigente',
    'mifid_product_governance',
    '32014L0065;32017R0565',
    'parcial',
    'official_esma_metadata',
    jsonb_build_object(
        'source_url', 'https://www.esma.europa.eu/document/guidelines-mifid-ii-product-governance-requirements-0',
        'sujeto_obligado', 'esi',
        'contract', 'guideline_esma',
        'verified_source', true,
        'note', 'Official current ESMA reference is ESMA35-43-3448.'
    )
)
ON CONFLICT (referencia) DO UPDATE SET
    tipo_documento = EXCLUDED.tipo_documento,
    organismo_emisor = EXCLUDED.organismo_emisor,
    jurisdiccion = EXCLUDED.jurisdiccion,
    tipo_fuente = EXCLUDED.tipo_fuente,
    ambito = EXCLUDED.ambito,
    fecha = EXCLUDED.fecha,
    titulo = EXCLUDED.titulo,
    texto = EXCLUDED.texto,
    url_fuente = EXCLUDED.url_fuente,
    fecha_publicacion = EXCLUDED.fecha_publicacion,
    estado_vigencia = EXCLUDED.estado_vigencia,
    ambito_tematico = EXCLUDED.ambito_tematico,
    regulacion_relacionada = EXCLUDED.regulacion_relacionada,
    row_completeness = EXCLUDED.row_completeness,
    row_provenance = EXCLUDED.row_provenance,
    metadata = EXCLUDED.metadata;

INSERT INTO obligacion_fuente (
    obligacion_id, fuente_tipo, codigo_referencia, articulo,
    descripcion, source_url, peso
)
SELECT op.id,
       'guideline_esma',
       'ESMA34-39-897',
       NULL,
       'ESMA guidelines on liquidity stress testing in UCITS and AIFs',
       'https://www.esma.europa.eu/document/guidelines-liquidity-stress-testing-in-ucits-and-aifs',
       2
FROM obligacion_perfil op
WHERE op.perfil_codigo = 'sgiic'
  AND op.descripcion ILIKE '%Politica de gestion de liquidez%'
  AND NOT EXISTS (
      SELECT 1
      FROM obligacion_fuente existing
      WHERE existing.obligacion_id = op.id
        AND existing.codigo_referencia = 'ESMA34-39-897'
  );

INSERT INTO obligacion_fuente (
    obligacion_id, fuente_tipo, codigo_referencia, articulo,
    descripcion, source_url, peso
)
SELECT op.id,
       'guideline_esma',
       'ESMA34-671404336-1364',
       NULL,
       'ESMA guidelines on liquidity management tools of UCITS and open-ended AIFs',
       'https://www.esma.europa.eu/document/guidelines-liquidity-management-tools-ucits-and-open-ended-aifs',
       2
FROM obligacion_perfil op
WHERE op.perfil_codigo = 'sgiic'
  AND op.descripcion ILIKE '%Reporte estres de liquidez%'
  AND NOT EXISTS (
      SELECT 1
      FROM obligacion_fuente existing
      WHERE existing.obligacion_id = op.id
        AND existing.codigo_referencia = 'ESMA34-671404336-1364'
  );

COMMIT;
