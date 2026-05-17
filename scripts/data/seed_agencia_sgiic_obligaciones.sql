-- Seed derived applicability obligations for agencia_valores and sgiic.
-- Preconditions:
--   - sociedad_valores obligations are already seeded.
--   - perfil_entidad has agencia_valores and sgiic.
-- Safe to rerun: destination obligations are UPSERTed and generated sources are refreshed.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM perfil_entidad WHERE codigo = 'agencia_valores') THEN
        RAISE EXCEPTION 'Required perfil_entidad agencia_valores is not loaded';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM perfil_entidad WHERE codigo = 'sgiic') THEN
        RAISE EXCEPTION 'Required perfil_entidad sgiic is not loaded';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM obligacion_perfil WHERE perfil_codigo = 'sociedad_valores') THEN
        RAISE EXCEPTION 'sociedad_valores obligations must be seeded before C-09';
    END IF;
END
$$;

DELETE FROM obligacion_fuente fuente
USING obligacion_perfil obligacion
WHERE fuente.obligacion_id = obligacion.id
  AND obligacion.perfil_codigo IN ('agencia_valores', 'sgiic');

WITH agencia_src AS (
    SELECT *
    FROM obligacion_perfil
    WHERE perfil_codigo = 'sociedad_valores'
      AND descripcion NOT ILIKE '%custodia%'
),
agencia_upsert AS (
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
        'agencia_valores',
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
        CURRENT_DATE,
        concat_ws(' ', notas, 'Perfil agencia_valores: aplicar con caveat de limitacion operativa y no custodia de activos segun LIVMC art. 144.')
    FROM agencia_src
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
    RETURNING id
),
sgiic_src AS (
    SELECT *
    FROM obligacion_perfil
    WHERE perfil_codigo = 'sociedad_valores'
      AND (
          norma_codigo = 'LEY10_2010'
          OR modelo_aeat IN ('111', '115', '187', '200')
      )
),
sgiic_upsert AS (
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
        'sgiic',
        obligacion_tipo,
        descripcion,
        periodicidad,
        plazo_descripcion,
        modelo_aeat,
        CASE WHEN modelo_aeat = '187' THEN 'RD_1082_2012' ELSE norma_codigo END,
        articulo_referencia,
        fuente_secundaria,
        evidencia_tipo,
        safe_to_answer,
        CASE WHEN modelo_aeat = '187' THEN false ELSE verified END,
        CASE WHEN modelo_aeat = '187' THEN 'parcial' ELSE completeness END,
        source_url,
        CURRENT_DATE,
        concat_ws(' ', notas, 'Perfil sgiic: obligacion derivada para gestora IIC; revisar alcance concreto de actividad.')
    FROM sgiic_src
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
    RETURNING id
),
sgiic_reporting AS (
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
    ) VALUES (
        'sgiic',
        'REPORTING',
        'Reporting periodico IIC a CNMV',
        'anual',
        'Periodicidad y formato sujetos a normativa IIC y circulares CNMV aplicables',
        NULL,
        'RD_1082_2012',
        NULL,
        'CNMV IIC',
        'norma_primaria',
        true,
        false,
        'parcial',
        'https://www.boe.es/buscar/act.php?id=BOE-A-2012-9716',
        CURRENT_DATE,
        'Obligacion SGIIC especifica. Articulo y circular CNMV concreta pendientes de mapeo granular.'
    )
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion) DO UPDATE SET
        periodicidad = EXCLUDED.periodicidad,
        plazo_descripcion = EXCLUDED.plazo_descripcion,
        norma_codigo = EXCLUDED.norma_codigo,
        verified = EXCLUDED.verified,
        completeness = EXCLUDED.completeness,
        source_url = EXCLUDED.source_url,
        capture_date = EXCLUDED.capture_date,
        notas = EXCLUDED.notas
    RETURNING id
)
SELECT
    (SELECT COUNT(*) FROM agencia_upsert) AS agencia_rows,
    (SELECT COUNT(*) FROM sgiic_upsert) AS sgiic_rows,
    (SELECT COUNT(*) FROM sgiic_reporting) AS sgiic_reporting_rows;

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
    dest.id,
    fuente.fuente_tipo,
    fuente.codigo_referencia,
    fuente.articulo,
    fuente.descripcion,
    fuente.source_url,
    fuente.peso
FROM obligacion_perfil dest
JOIN obligacion_perfil src
  ON src.perfil_codigo = 'sociedad_valores'
 AND src.obligacion_tipo = dest.obligacion_tipo
 AND src.descripcion = dest.descripcion
JOIN obligacion_fuente fuente ON fuente.obligacion_id = src.id
WHERE dest.perfil_codigo IN ('agencia_valores', 'sgiic');

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
    'norma_primaria',
    'RD_1082_2012',
    NULL,
    descripcion,
    'https://www.boe.es/buscar/act.php?id=BOE-A-2012-9716',
    1
FROM obligacion_perfil
WHERE perfil_codigo = 'sgiic'
  AND descripcion = 'Reporting periodico IIC a CNMV';

COMMIT;
