-- Seed CNMV/market obligations for perfil_entidad='sociedad_valores'.
-- Preconditions:
--   - LIVMC, MIFIR_2014_60 and CRR_II_2019_2057 are loaded in norma.
--   - CNMV circulars are loaded in documento_interpretativo.
-- Safe to rerun: obligation rows are UPSERTed and generated sources are refreshed.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM perfil_entidad WHERE codigo = 'sociedad_valores') THEN
        RAISE EXCEPTION 'Required perfil_entidad sociedad_valores is not loaded';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LIVMC') THEN
        RAISE EXCEPTION 'Required norma LIVMC is not loaded';
    END IF;
END
$$;

CREATE TEMP TABLE tmp_cnmv_circular AS
SELECT referencia, titulo, url_fuente AS source_url
FROM documento_interpretativo
WHERE tipo_documento = 'circular_cnmv'
  AND url_fuente IS NOT NULL
  AND url_fuente <> ''
  AND (
      ambito ILIKE '%ESI%'
      OR titulo ILIKE '%informacion%'
      OR titulo ILIKE '%prudencial%'
      OR titulo ILIKE '%MiFID%'
  )
ORDER BY fecha_publicacion DESC NULLS LAST, id DESC
LIMIT 1;

DO $$
DECLARE
    missing_livmc_articles TEXT;
BEGIN
    SELECT string_agg(required.numero, ', ' ORDER BY required.numero)
    INTO missing_livmc_articles
    FROM (VALUES ('125'), ('228')) AS required(numero)
    WHERE NOT EXISTS (
        SELECT 1
        FROM articulo a
        JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo = 'LIVMC'
          AND a.numero = required.numero
    );

    IF missing_livmc_articles IS NOT NULL THEN
        RAISE EXCEPTION 'Missing LIVMC articles: %', missing_livmc_articles;
    END IF;
END
$$;

WITH target AS (
    SELECT *
    FROM (
        VALUES
        ('REPORTING', 'Informacion financiera periodica a CNMV'),
        ('REPORTING', 'Reporte prudencial de recursos propios'),
        ('REPORTING', 'MiFIR transaction reporting'),
        ('REPORTING', 'Comunicacion de participaciones significativas'),
        ('CONTROL_INTERNO', 'Politica de conflictos de interes'),
        ('CONTROL_INTERNO', 'Politica de mejor ejecucion'),
        ('FORMACION', 'Certificacion MiFID II del personal que presta servicios')
    ) AS raw(obligacion_tipo, descripcion)
)
DELETE FROM obligacion_fuente fuente
USING obligacion_perfil obligacion, target
WHERE fuente.obligacion_id = obligacion.id
  AND obligacion.perfil_codigo = 'sociedad_valores'
  AND obligacion.obligacion_tipo = target.obligacion_tipo
  AND obligacion.descripcion = target.descripcion;

WITH seed AS (
    SELECT *
    FROM (
        VALUES
        (
            'REPORTING',
            'Informacion financiera periodica a CNMV',
            'semestral',
            'Informacion semestral y anual cuando resulte aplicable',
            NULL,
            'LIVMC',
            'art. 228',
            true,
            'parcial',
            'Obligacion condicionada al perimetro de informacion periodica aplicable a la entidad.'
        ),
        (
            'REPORTING',
            'Reporte prudencial de recursos propios',
            'trimestral',
            'Periodicidad prudencial sujeta a regimen CRR/IFR aplicable',
            NULL,
            'CRR_II_2019_2057',
            NULL,
            false,
            'parcial',
            'CRR/IFR aplicable pendiente de granularidad por articulo; no usar como obligacion universal sin validar regimen prudencial concreto.'
        ),
        (
            'REPORTING',
            'MiFIR transaction reporting',
            'diaria',
            'T+1 cuando ejecuta transacciones sujetas a reporte',
            NULL,
            'MIFIR_2014_60',
            NULL,
            false,
            'parcial',
            'Solo si ejecuta transacciones en instrumentos financieros sujetos a obligacion de reporte; articulo MiFIR pendiente de carga granular.'
        ),
        (
            'REPORTING',
            'Comunicacion de participaciones significativas',
            'ad_hoc',
            'Cuando se alcance, supere o reduzca un umbral legal aplicable',
            NULL,
            'LIVMC',
            'art. 125',
            true,
            'parcial',
            'Obligacion condicionada a superar umbrales de participacion significativa.'
        ),
        (
            'CONTROL_INTERNO',
            'Politica de conflictos de interes',
            'anual',
            'Revision anual y cuando cambie la actividad o el mapa de conflictos',
            NULL,
            'LIVMC',
            'MiFID II art. 23',
            false,
            'parcial',
            'Referencia UE confirmada como criterio MiFID II; articulo LIVMC especifico pendiente de mapeo.'
        ),
        (
            'CONTROL_INTERNO',
            'Politica de mejor ejecucion',
            'anual',
            'Revision anual y publicacion/informe cuando aplique',
            NULL,
            'LIVMC',
            'MiFID II art. 27',
            false,
            'parcial',
            'Referencia UE confirmada como criterio MiFID II; articulo LIVMC especifico pendiente de mapeo.'
        ),
        (
            'FORMACION',
            'Certificacion MiFID II del personal que presta servicios',
            'continua',
            'Verificacion en contratacion y revision durante la prestacion de servicios',
            NULL,
            'LIVMC',
            NULL,
            false,
            'parcial',
            'Obligacion de conocimientos y competencia MiFID II pendiente de articulo normativo concreto.'
        )
    ) AS raw(
        obligacion_tipo,
        descripcion,
        periodicidad,
        plazo_descripcion,
        modelo_aeat,
        norma_codigo,
        articulo_referencia,
        verified,
        completeness,
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
        seed.obligacion_tipo,
        seed.descripcion,
        seed.periodicidad,
        seed.plazo_descripcion,
        seed.modelo_aeat,
        seed.norma_codigo,
        seed.articulo_referencia,
        COALESCE((SELECT referencia FROM tmp_cnmv_circular LIMIT 1), 'CNMV'),
        CASE
            WHEN seed.norma_codigo IN ('MIFIR_2014_60', 'CRR_II_2019_2057') THEN 'reglamento_ue'
            ELSE 'norma_primaria'
        END,
        true,
        seed.verified,
        seed.completeness,
        CASE seed.norma_codigo
            WHEN 'LIVMC' THEN 'https://www.boe.es/buscar/act.php?id=BOE-A-2023-7053'
            WHEN 'MIFIR_2014_60' THEN 'https://eur-lex.europa.eu/eli/reg/2014/600/oj'
            WHEN 'CRR_II_2019_2057' THEN 'https://eur-lex.europa.eu/eli/reg/2019/876/oj'
            ELSE 'https://www.cnmv.es/portal/Menu/Normativa'
        END,
        CURRENT_DATE,
        seed.notas
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
    RETURNING id, descripcion, norma_codigo, articulo_referencia, fuente_secundaria, source_url
),
primary_sources AS (
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
        id,
        CASE
            WHEN norma_codigo IN ('MIFIR_2014_60', 'CRR_II_2019_2057') THEN 'reglamento_ue'
            ELSE 'norma_primaria'
        END,
        norma_codigo,
        articulo_referencia,
        descripcion,
        source_url,
        1
    FROM upserted
    WHERE norma_codigo IS NOT NULL
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
    'circular',
    tmp.referencia,
    NULL,
    tmp.titulo,
    tmp.source_url,
    2
FROM upserted
CROSS JOIN tmp_cnmv_circular tmp;

COMMIT;
