-- Seed PBC/FT obligations for perfil_entidad='sociedad_valores'.
-- Preconditions:
--   - LEY10_2010 and RD_304_2014 articles listed below are loaded.
--   - SEPBLAC granular rows are loaded; rows with sujeto_obligado='all' are used as secondary guidance.
-- Safe to rerun: obligation rows are UPSERTed and generated sources are refreshed.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM perfil_entidad WHERE codigo = 'sociedad_valores') THEN
        RAISE EXCEPTION 'Required perfil_entidad sociedad_valores is not loaded';
    END IF;
END
$$;

CREATE TEMP TABLE tmp_sepblac_obligacion AS
SELECT url_fuente AS source_url
FROM documento_interpretativo
WHERE tipo_documento = 'obligacion_sepblac'
  AND COALESCE(metadata->>'sujeto_obligado', '') IN ('sociedad_valores', 'esi', 'all')
  AND url_fuente IS NOT NULL
  AND url_fuente <> ''
ORDER BY CASE COALESCE(metadata->>'sujeto_obligado', '') WHEN 'sociedad_valores' THEN 1 WHEN 'esi' THEN 2 ELSE 3 END, id
LIMIT 1;

DO $$
DECLARE
    missing_articles TEXT;
BEGIN
    SELECT string_agg(required.codigo || ' ' || required.numero, ', ' ORDER BY required.codigo, required.numero)
    INTO missing_articles
    FROM (
        VALUES
            ('LEY10_2010', '3'), ('LEY10_2010', '4'), ('LEY10_2010', '11'),
            ('LEY10_2010', '12'), ('LEY10_2010', '18'), ('LEY10_2010', '25'),
            ('LEY10_2010', '26'), ('LEY10_2010', '26 bis'), ('LEY10_2010', '29'),
            ('RD_304_2014', '4'), ('RD_304_2014', '8'), ('RD_304_2014', '15'),
            ('RD_304_2014', '16'), ('RD_304_2014', '33'), ('RD_304_2014', '35'),
            ('RD_304_2014', '36'), ('RD_304_2014', '40')
    ) AS required(codigo, numero)
    WHERE NOT EXISTS (
        SELECT 1
        FROM articulo a
        JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo = required.codigo
          AND a.numero = required.numero
    );

    IF missing_articles IS NOT NULL THEN
        RAISE EXCEPTION 'Missing PBC/FT articles: %', missing_articles;
    END IF;
END
$$;

DELETE FROM obligacion_fuente fuente
USING obligacion_perfil obligacion
WHERE fuente.obligacion_id = obligacion.id
  AND obligacion.perfil_codigo = 'sociedad_valores'
  AND obligacion.obligacion_tipo IN (
      'DILIGENCIA_DEBIDA',
      'COMUNICACION_INDICIO',
      'CONTROL_INTERNO',
      'FORMACION',
      'REGISTRO'
  );

WITH seed AS (
    SELECT *
    FROM (
        VALUES
        (
            'DILIGENCIA_DEBIDA',
            'Identificacion formal y verificacion del cliente',
            'continua',
            'En cada relacion de negocio y durante su seguimiento',
            'art. 3',
            'art. 4',
            'Identificar formalmente y verificar la identidad del cliente antes o durante la relacion de negocio.'
        ),
        (
            'DILIGENCIA_DEBIDA',
            'Identificacion del titular real UBO',
            'continua',
            'Antes o durante la relacion de negocio y con actualizacion continua',
            'art. 4',
            'art. 8',
            'Identificar el titular real de la relacion u operacion.'
        ),
        (
            'DILIGENCIA_DEBIDA',
            'Diligencia reforzada para PEPs y riesgo alto',
            'continua',
            'Revision periodica y aplicacion reforzada cuando concurra riesgo alto',
            'arts. 11-12',
            'arts. 15-16',
            'Aplicar medidas reforzadas en supuestos de personas con responsabilidad publica y alto riesgo.'
        ),
        (
            'COMUNICACION_INDICIO',
            'Comunicacion de operaciones sospechosas al SEPBLAC',
            'ad_hoc',
            'Cuando se detecte indicio o certeza de relacion con blanqueo o financiacion del terrorismo',
            'art. 18',
            NULL,
            'Comunicar por iniciativa propia hechos u operaciones respecto de los que exista indicio.'
        ),
        (
            'CONTROL_INTERNO',
            'Manual de prevencion PBC/FT',
            'anual',
            'Revision minima anual o cuando cambie el riesgo, la actividad o la normativa aplicable',
            'art. 26',
            'art. 35',
            'Mantener politicas y procedimientos internos de prevencion adaptados al riesgo.'
        ),
        (
            'CONTROL_INTERNO',
            'Organo de control interno y representante ante SEPBLAC',
            'continua',
            'Obligacion permanente mientras la entidad sea sujeto obligado',
            'art. 26 bis',
            'art. 36',
            'Designar y mantener estructura interna de control y representante ante SEPBLAC.'
        ),
        (
            'FORMACION',
            'Formacion PBC/FT a empleados',
            'anual',
            'Plan anual de formacion para empleados y directivos relevantes',
            'art. 29',
            'art. 40',
            'Aprobar y ejecutar planes de formacion en prevencion PBC/FT.'
        ),
        (
            'REGISTRO',
            'Conservacion de documentacion PBC/FT durante 10 anos',
            'continua',
            'Conservacion durante 10 anos desde terminacion de relacion o ejecucion de operacion',
            'art. 25',
            'art. 33',
            'Conservar documentos de diligencia debida, operaciones y comunicaciones conforme a plazo legal.'
        )
    ) AS raw(
        obligacion_tipo,
        descripcion,
        periodicidad,
        plazo_descripcion,
        ley_articulo,
        rd_articulo,
        notas
    )
),
upserted AS (
    INSERT INTO obligacion_perfil (
        perfil_codigo,
        obligacion_tipo,
        descripcion,
        periodicidad,
        plazo_descripcion,
        modelo_aeat,
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
        'sociedad_valores',
        obligacion_tipo,
        descripcion,
        periodicidad,
        plazo_descripcion,
        NULL,
        'LEY10_2010',
        CASE
            WHEN rd_articulo IS NULL THEN ley_articulo
            ELSE ley_articulo || '; RD_304_2014 ' || rd_articulo
        END,
        'SEPBLAC obligaciones',
        'norma_primaria',
        true,
        true,
        'completa',
        'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6146',
        CURRENT_DATE,
        notas
    FROM seed
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion) DO UPDATE SET
        periodicidad = EXCLUDED.periodicidad,
        plazo_descripcion = EXCLUDED.plazo_descripcion,
        modelo_aeat = EXCLUDED.modelo_aeat,
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
    RETURNING id, descripcion, articulo_referencia, fuente_secundaria
),
ley_sources AS (
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
        upserted.id,
        'norma_primaria',
        'LEY10_2010',
        split_part(upserted.articulo_referencia, ';', 1),
        upserted.descripcion,
        'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6146',
        1
    FROM upserted
    RETURNING 1
),
rd_sources AS (
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
        upserted.id,
        'norma_primaria',
        'RD_304_2014',
        trim(split_part(upserted.articulo_referencia, 'RD_304_2014', 2)),
        upserted.descripcion,
        'https://www.boe.es/buscar/act.php?id=BOE-A-2014-5438',
        1
    FROM upserted
    WHERE upserted.articulo_referencia LIKE '%RD_304_2014%'
    RETURNING 1
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
    upserted.id,
    'guia_operativa',
    'SEPBLAC_obligaciones',
    NULL,
    upserted.descripcion,
    tmp.source_url,
    2
FROM upserted
CROSS JOIN tmp_sepblac_obligacion tmp;

COMMIT;
