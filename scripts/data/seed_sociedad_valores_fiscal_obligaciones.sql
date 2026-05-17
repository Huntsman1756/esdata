-- Seed fiscal AEAT obligations for perfil_entidad='sociedad_valores'.
-- Preconditions:
--   - perfil_entidad has sociedad_valores.
--   - AEAT models listed below exist and have official URL metadata.
--   - Core normas/articles are loaded for verified obligations.
-- Safe to rerun: obligation rows are UPSERTed and generated sources are refreshed.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM perfil_entidad WHERE codigo = 'sociedad_valores') THEN
        RAISE EXCEPTION 'Required perfil_entidad sociedad_valores is not loaded';
    END IF;
END
$$;

CREATE TEMP TABLE tmp_modelo_source AS
SELECT
    m.codigo,
    COALESCE(c.url_instrucciones, m.url_info, c.url_normativa) AS source_url
FROM aeat_modelo m
LEFT JOIN modelo_campana c
    ON c.modelo_id = m.id
   AND c.activo = true
WHERE m.codigo IN ('111', '115', '187', '193', '198', '200', '216', '289', '290', '296', '303');

DO $$
DECLARE
    missing_models TEXT;
BEGIN
    SELECT string_agg(codigo, ', ' ORDER BY codigo)
    INTO missing_models
    FROM (
        VALUES ('111'), ('115'), ('187'), ('193'), ('198'), ('200'),
               ('216'), ('289'), ('290'), ('296'), ('303')
    ) AS required(codigo)
    WHERE NOT EXISTS (
        SELECT 1
        FROM tmp_modelo_source source
        WHERE source.codigo = required.codigo
          AND source.source_url IS NOT NULL
          AND source.source_url <> ''
    );

    IF missing_models IS NOT NULL THEN
        RAISE EXCEPTION 'Missing AEAT official source URL for models: %', missing_models;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM articulo a JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo = 'LIRPF' AND a.numero = '101'
    ) THEN
        RAISE EXCEPTION 'Required article LIRPF art. 101 is not loaded';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM articulo a JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo = 'LIVA' AND a.numero = '164'
    ) THEN
        RAISE EXCEPTION 'Required article LIVA art. 164 is not loaded';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM articulo a JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo = 'LIS' AND a.numero = '124'
    ) THEN
        RAISE EXCEPTION 'Required article LIS art. 124 is not loaded';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM articulo a JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo = 'TRLIRNR' AND a.numero = '31'
    ) THEN
        RAISE EXCEPTION 'Required article TRLIRNR art. 31 is not loaded';
    END IF;
END
$$;

DELETE FROM obligacion_fuente fuente
USING obligacion_perfil obligacion
WHERE fuente.obligacion_id = obligacion.id
  AND obligacion.perfil_codigo = 'sociedad_valores'
  AND obligacion.obligacion_tipo IN ('AUTOLIQUIDACION', 'DECLARACION_INFORMATIVA');

WITH seed AS (
    SELECT *
    FROM (
        VALUES
        (
            'AUTOLIQUIDACION',
            'Modelo 111 - Retenciones trabajo y actividades profesionales',
            'mensual',
            'mensual o trimestral segun volumen y condiciones AEAT',
            '111',
            'LIRPF',
            'art. 101',
            true,
            'completa',
            NULL
        ),
        (
            'AUTOLIQUIDACION',
            'Modelo 115 - Retenciones por arrendamientos urbanos',
            'trimestral',
            NULL,
            '115',
            'LIRPF',
            'art. 101',
            true,
            'completa',
            NULL
        ),
        (
            'AUTOLIQUIDACION',
            'Modelo 303 - IVA autoliquidacion',
            'mensual',
            'mensual o trimestral segun volumen y condiciones AEAT',
            '303',
            'LIVA',
            'art. 164',
            true,
            'parcial',
            'Servicios financieros exentos IVA art. 20 LIVA. Aplicabilidad condicional: verificar actividad concreta.'
        ),
        (
            'AUTOLIQUIDACION',
            'Modelo 200 - Impuesto sobre Sociedades declaracion anual',
            'anual',
            '25 dias naturales siguientes a los 6 meses posteriores al cierre',
            '200',
            'LIS',
            'art. 124',
            true,
            'completa',
            NULL
        ),
        (
            'DECLARACION_INFORMATIVA',
            'Modelo 187 - Acciones y participaciones de IIC',
            'anual',
            'enero',
            '187',
            'RD_1082_2012',
            NULL,
            false,
            'parcial',
            'Solo si intermedia en suscripcion, reembolso o transmision de IIC. Articulo concreto pendiente de verificacion.'
        ),
        (
            'DECLARACION_INFORMATIVA',
            'Modelo 193 - Retenciones capital mobiliario',
            'anual',
            'enero',
            '193',
            'LIRPF',
            'art. 101',
            true,
            'completa',
            NULL
        ),
        (
            'DECLARACION_INFORMATIVA',
            'Modelo 198 - Operaciones con activos financieros y valores',
            'anual',
            'enero-febrero',
            '198',
            NULL,
            NULL,
            false,
            'parcial',
            'Norma y articulo especifico pendientes de verificacion; fuente operativa AEAT cargada.'
        ),
        (
            'DECLARACION_INFORMATIVA',
            'Modelo 289 - CRS cuentas financieras',
            'anual',
            'enero',
            '289',
            'LGT',
            NULL,
            false,
            'parcial',
            'Solo si es institucion financiera obligada CRS. Articulo especifico pendiente de verificacion.'
        ),
        (
            'DECLARACION_INFORMATIVA',
            'Modelo 290 - FATCA cuentas financieras',
            'anual',
            'enero',
            '290',
            NULL,
            NULL,
            false,
            'parcial',
            'Solo si tiene cuentas de US persons o passive NFFE con substantial US owner. Ver modelo_regla_inclusion.'
        ),
        (
            'DECLARACION_INFORMATIVA',
            'Modelo 296 - IRNR retenciones resumen anual',
            'anual',
            NULL,
            '296',
            'TRLIRNR',
            'art. 31',
            true,
            'parcial',
            'Solo si tiene clientes no residentes con rendimientos sujetos a retencion.'
        ),
        (
            'AUTOLIQUIDACION',
            'Modelo 216 - IRNR retenciones periodicas',
            'mensual',
            'mensual o trimestral segun volumen y condiciones AEAT',
            '216',
            'TRLIRNR',
            'art. 31',
            true,
            'completa',
            NULL
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
        'AEAT modelo ' || seed.modelo_aeat,
        'norma_primaria',
        true,
        seed.verified,
        seed.completeness,
        source.source_url,
        CURRENT_DATE,
        seed.notas
    FROM seed
    JOIN tmp_modelo_source source ON source.codigo = seed.modelo_aeat
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
    RETURNING id, modelo_aeat, norma_codigo, articulo_referencia, descripcion, source_url
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
    id,
    'norma_primaria',
    norma_codigo,
    articulo_referencia,
    descripcion,
    CASE norma_codigo
        WHEN 'LIRPF' THEN 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764'
        WHEN 'LIVA' THEN 'https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740'
        WHEN 'LIS' THEN 'https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328'
        WHEN 'TRLIRNR' THEN 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-4527'
        WHEN 'RD_1082_2012' THEN 'https://www.boe.es/buscar/act.php?id=BOE-A-2012-9716'
        WHEN 'LGT' THEN 'https://www.boe.es/buscar/act.php?id=BOE-A-2003-23186'
    END,
    1
FROM upserted
WHERE norma_codigo IS NOT NULL;

COMMIT;
