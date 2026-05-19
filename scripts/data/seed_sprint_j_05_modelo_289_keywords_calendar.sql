BEGIN;

WITH modelo AS (
    SELECT id AS modelo_id
    FROM aeat_modelo
    WHERE codigo = '289'
    LIMIT 1
),
campana AS (
    SELECT mc.id AS campana_id
    FROM modelo_campana mc
    JOIN modelo m ON m.modelo_id = mc.modelo_id
    ORDER BY mc.id DESC
    LIMIT 1
),
keywords AS (
    SELECT
        modelo.modelo_id,
        data.keyword,
        data.dominio
    FROM modelo
    CROSS JOIN (
        VALUES
        ('CRS', 'fiscal_crs'),
        ('Common Reporting Standard', 'fiscal_crs'),
        ('DAC2', 'fiscal_crs'),
        ('intercambio automatico', 'fiscal_crs'),
        ('cuentas financieras asistencia mutua', 'fiscal_crs'),
        ('institucion financiera obligada', 'fiscal_crs'),
        ('residencia fiscal no residente', 'fiscal_crs'),
        ('cuenta reportable', 'fiscal_crs'),
        ('NFE pasiva', 'fiscal_crs'),
        ('entidad no financiera pasiva', 'fiscal_crs'),
        ('modelo 289', 'fiscal_crs'),
        ('289', 'fiscal_crs')
    ) AS data(keyword, dominio)
)
INSERT INTO modelo_trigger_keyword (
    modelo_id,
    keyword,
    dominio
)
SELECT
    modelo_id,
    keyword,
    dominio
FROM keywords k
WHERE NOT EXISTS (
    SELECT 1
    FROM modelo_trigger_keyword mtk
    WHERE mtk.modelo_id = k.modelo_id
      AND lower(mtk.keyword) = lower(k.keyword)
);

INSERT INTO modelo_fiscal_calendar (
    campana_id,
    fecha_inicio_presentacion,
    fecha_fin_presentacion,
    observaciones,
    fuente,
    activo
)
WITH modelo AS (
    SELECT id AS modelo_id
    FROM aeat_modelo
    WHERE codigo = '289'
    LIMIT 1
),
campana AS (
    SELECT mc.id AS campana_id
    FROM modelo_campana mc
    JOIN modelo m ON m.modelo_id = mc.modelo_id
    ORDER BY mc.id DESC
    LIMIT 1
)
SELECT
    campana_id,
    TIMESTAMP '2026-01-01 00:00:00',
    TIMESTAMP '2026-05-31 23:59:59',
    'Modelo 289 CRS - presentacion anual de enero a mayo respecto del ejercicio anterior',
    'https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml',
    TRUE
FROM campana c
WHERE NOT EXISTS (
    SELECT 1
    FROM modelo_fiscal_calendar mfc
    WHERE mfc.campana_id = c.campana_id
      AND mfc.fecha_inicio_presentacion = TIMESTAMP '2026-01-01 00:00:00'
);

COMMIT;
