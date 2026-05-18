\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LIS') THEN
        RAISE EXCEPTION 'Missing norma LIS';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM aeat_modelo WHERE codigo = '202') THEN
        RAISE EXCEPTION 'Missing aeat_modelo 202';
    END IF;
END $$;

WITH target_profiles(perfil_codigo) AS (
    VALUES
        ('sociedad_valores'),
        ('agencia_valores'),
        ('eaf'),
        ('entidad_credito'),
        ('sgiic'),
        ('empresa_servicios_pago')
),
inserted AS (
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
        tp.perfil_codigo,
        'AUTOLIQUIDACION',
        'Modelo 202 - Pago fraccionado IS',
        'trimestral',
        'Del 1 al 20 de abril, octubre y diciembre',
        '202',
        'LIS',
        'art. 40',
        'Orden HFP/583/2023 (aprobacion Modelo 202)',
        'norma_primaria',
        true,
        true,
        'parcial',
        'https://sede.agenciatributaria.gob.es/Sede/impuesto-sobre-sociedades/modelo-202.html',
        CURRENT_DATE,
        'Condicional: solo si procede efectuar pago fraccionado del IS. Base legal LIS art. 40: primeros 20 dias naturales de abril, octubre y diciembre. Metodo art. 40.2: 18% sobre cuota del ultimo periodo. Metodo art. 40.3: sobre base imponible acumulada de 3, 9 u 11 meses; obligatorio si INCN supera 6M EUR. No aplica a entidades excluidas por LIS art. 40.1.'
    FROM target_profiles tp
    WHERE NOT EXISTS (
        SELECT 1
        FROM obligacion_perfil op
        WHERE op.perfil_codigo = tp.perfil_codigo
          AND op.modelo_aeat = '202'
    )
    RETURNING id
),
all_m202 AS (
    SELECT id
    FROM inserted
    UNION
    SELECT id
    FROM obligacion_perfil
    WHERE modelo_aeat = '202'
      AND perfil_codigo IN (
          'sociedad_valores',
          'agencia_valores',
          'eaf',
          'entidad_credito',
          'sgiic',
          'empresa_servicios_pago'
      )
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
    m.id,
    'norma_primaria',
    'LIS',
    'art. 40',
    'Ley 27/2014 del Impuesto sobre Sociedades: pago fraccionado',
    'https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328#a40',
    1
FROM all_m202 m
WHERE NOT EXISTS (
    SELECT 1
    FROM obligacion_fuente ofu
    WHERE ofu.obligacion_id = m.id
      AND ofu.codigo_referencia = 'LIS'
      AND ofu.articulo = 'art. 40'
);
