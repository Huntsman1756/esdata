-- Sprint L L-03: link selected normativa_esi_cnmv rows to obligacion_perfil.
--
-- Scope is intentionally narrow and traceable:
-- - Circular 1/2013 CNMV: comunicaciones de informacion a CNMV.
-- - Circular 1/2010 CNMV: informacion estadistica CNMV.

WITH docs AS (
    SELECT referencia, titulo, url_fuente
    FROM documento_interpretativo
    WHERE referencia IN (
        'CNMV-NORMATIVA-ESI-circular-1-2013',
        'CNMV-NORMATIVA-ESI-circular-1-2010'
    )
      AND tipo_documento = 'normativa_esi_cnmv'
      AND estado_vigencia <> 'derogada'
),
normas AS (
    INSERT INTO norma (
        codigo,
        titulo,
        boe_id,
        jurisdiccion,
        tipo_fuente,
        tipo_documento,
        ambito,
        estado_cobertura,
        vigente_desde,
        tipo_norma,
        url_eurlex,
        vigente
    )
    VALUES
        (
            'CNMV_CIRC_1_2013',
            'Circular 1/2013 CNMV sobre comunicacion de informaciones a la CNMV',
            'CNMV-NORMATIVA-ESI-circular-1-2013',
            'es',
            'cnmv',
            'circular_cnmv',
            'mercados_financieros_es',
            'metadata_official',
            DATE '2013-02-14',
            'circular_cnmv',
            'http://boe.es/buscar/doc.php?id=BOE-A-2013-1785',
            TRUE
        ),
        (
            'CNMV_CIRC_1_2010',
            'Circular 1/2010 CNMV sobre informacion estadistica de empresas de servicios de inversion',
            'CNMV-NORMATIVA-ESI-circular-1-2010',
            'es',
            'cnmv',
            'circular_cnmv',
            'mercados_financieros_es',
            'metadata_official',
            DATE '2010-07-28',
            'circular_cnmv',
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2010-13162',
            TRUE
        )
    ON CONFLICT (codigo) DO UPDATE
    SET titulo = EXCLUDED.titulo,
        boe_id = EXCLUDED.boe_id,
        jurisdiccion = EXCLUDED.jurisdiccion,
        tipo_fuente = EXCLUDED.tipo_fuente,
        tipo_documento = EXCLUDED.tipo_documento,
        ambito = EXCLUDED.ambito,
        estado_cobertura = EXCLUDED.estado_cobertura,
        vigente_desde = EXCLUDED.vigente_desde,
        tipo_norma = EXCLUDED.tipo_norma,
        url_eurlex = EXCLUDED.url_eurlex,
        vigente = EXCLUDED.vigente
    RETURNING codigo
),
profiles AS (
    SELECT *
    FROM (VALUES
        ('sociedad_valores'::varchar),
        ('agencia_valores'::varchar),
        ('sgiic'::varchar)
    ) AS p(perfil_codigo)
),
obligation_rows AS (
    SELECT
        p.perfil_codigo,
        'REPORTING'::varchar AS obligacion_tipo,
        'Comunicacion de informaciones a CNMV (Circular 1/2013)'::text AS descripcion,
        'continua'::varchar AS periodicidad,
        'CNMV_CIRC_1_2013'::varchar AS norma_codigo,
        'Circular 1/2013 CNMV'::text AS articulo_referencia,
        'CNMV normativa ESI'::text AS fuente_secundaria,
        'official_exact'::varchar AS evidencia_tipo,
        TRUE AS safe_to_answer,
        TRUE AS verified,
        'parcial'::varchar AS completeness,
        'http://boe.es/buscar/doc.php?id=BOE-A-2013-1785'::text AS source_url,
        'Obligacion derivada de normativa ESI CNMV cargada como documento oficial. Aplicabilidad conservadora a ESI y SGIIC; revisar caso concreto y duplicidad con obligaciones MiFID/LIVMC antes de respuesta material.'::text AS notas
    FROM profiles p
    UNION ALL
    SELECT
        p.perfil_codigo,
        'REPORTING',
        'Informacion estadistica a CNMV (Circular 1/2010)',
        'continua',
        'CNMV_CIRC_1_2010',
        'Circular 1/2010 CNMV',
        'CNMV normativa ESI',
        'official_exact',
        TRUE,
        TRUE,
        'parcial',
        'https://www.boe.es/buscar/doc.php?id=BOE-A-2010-13162',
        'Obligacion derivada de normativa ESI CNMV cargada como documento oficial. Aplicabilidad conservadora a ESI y SGIIC; revisar caso concreto y duplicidad con obligaciones MiFID/LIVMC antes de respuesta material.'
    FROM profiles p
),
upserted AS (
    INSERT INTO obligacion_perfil (
        perfil_codigo,
        obligacion_tipo,
        descripcion,
        periodicidad,
        norma_codigo,
        articulo_referencia,
        fuente_secundaria,
        evidencia_tipo,
        safe_to_answer,
        verified,
        completeness,
        source_url,
        capture_date,
        notas
    )
    SELECT
        perfil_codigo,
        obligacion_tipo,
        descripcion,
        periodicidad,
        norma_codigo,
        articulo_referencia,
        fuente_secundaria,
        evidencia_tipo,
        safe_to_answer,
        verified,
        completeness,
        source_url,
        CURRENT_DATE,
        notas
    FROM obligation_rows
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion) DO UPDATE
    SET periodicidad = EXCLUDED.periodicidad,
        norma_codigo = EXCLUDED.norma_codigo,
        articulo_referencia = EXCLUDED.articulo_referencia,
        fuente_secundaria = EXCLUDED.fuente_secundaria,
        evidencia_tipo = EXCLUDED.evidencia_tipo,
        safe_to_answer = EXCLUDED.safe_to_answer,
        verified = EXCLUDED.verified,
        completeness = EXCLUDED.completeness,
        source_url = EXCLUDED.source_url,
        capture_date = EXCLUDED.capture_date,
        notas = EXCLUDED.notas
    RETURNING id, norma_codigo, articulo_referencia, descripcion, source_url
)
INSERT INTO obligacion_fuente (
    obligacion_id,
    fuente_tipo,
    codigo_referencia,
    articulo,
    descripcion,
    source_url,
    peso
)
SELECT
    u.id,
    'documento_cnmv',
    u.norma_codigo,
    u.articulo_referencia,
    'Normativa ESI CNMV verificada: ' || u.descripcion,
    u.source_url,
    1
FROM upserted u
WHERE NOT EXISTS (
    SELECT 1
    FROM obligacion_fuente f
    WHERE f.obligacion_id = u.id
      AND f.codigo_referencia = u.norma_codigo
      AND f.articulo = u.articulo_referencia
      AND f.source_url = u.source_url
);

INSERT INTO cnmv_obligation_link (documento_referencia, tipo_obligacion, nota)
SELECT referencia, 'obligacion_perfil', titulo
FROM documento_interpretativo d
WHERE d.referencia IN (
        'CNMV-NORMATIVA-ESI-circular-1-2013',
        'CNMV-NORMATIVA-ESI-circular-1-2010'
    )
  AND d.tipo_documento = 'normativa_esi_cnmv'
  AND d.estado_vigencia <> 'derogada'
  AND NOT EXISTS (
      SELECT 1
      FROM cnmv_obligation_link l
      WHERE l.documento_referencia = d.referencia
        AND l.tipo_obligacion = 'obligacion_perfil'
  );
