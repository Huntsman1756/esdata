-- Explicit completeness markers for the AEAT 29-model audit.
-- Run through docker compose exec postgres psql, never via host-side DB clients.

ALTER TABLE modelo_campana_operativa
ADD COLUMN IF NOT EXISTS completeness_estado TEXT;

ALTER TABLE modelo_campana_operativa
DROP CONSTRAINT IF EXISTS ck_modelo_campana_operativa_completeness_estado;

ALTER TABLE modelo_campana_operativa
ADD CONSTRAINT ck_modelo_campana_operativa_completeness_estado
CHECK (
    completeness_estado IS NULL
    OR completeness_estado IN (
        'completa',
        'parcial',
        'no-casillas-expected',
        'deprecated'
    )
);

WITH target(codigo, completeness_estado, nota_completeness) AS (
    VALUES
        ('102', 'no-casillas-expected', 'M-04: documento de ingreso segundo plazo IRPF; no se espera inventario estructurado de casillas independiente.'),
        ('146', 'no-casillas-expected', 'M-04: formulario/comunicacion descargable sin diseno de registro estructurado localizado.'),
        ('147', 'no-casillas-expected', 'M-04: comunicacion descargable sin diseno de registro estructurado localizado.'),
        ('186', 'no-casillas-expected', 'M-04: procedimiento informativo sin diseno especifico localizado.'),
        ('206', 'no-casillas-expected', 'M-04: documento de ingreso/devolucion vinculado a modelo 200, sin diseno independiente.'),
        ('247', 'no-casillas-expected', 'M-04: comunicacion descargable sin diseno de registro estructurado localizado.')
),
active_campaign AS (
    SELECT DISTINCT ON (m.codigo)
        m.codigo,
        mc.id AS campana_id,
        t.completeness_estado,
        t.nota_completeness
    FROM target t
    JOIN aeat_modelo m ON m.codigo = t.codigo AND COALESCE(m.activo, true) = true
    JOIN modelo_campana mc ON mc.modelo_id = m.id AND mc.activo = true
    ORDER BY m.codigo, mc.campana DESC
)
INSERT INTO modelo_campana_operativa (
    campana_id,
    nota,
    origen_metadato,
    estado_metadato,
    completeness_estado,
    actualizado_at
)
SELECT
    campana_id,
    nota_completeness,
    'seed_curado',
    'curado',
    completeness_estado,
    now()
FROM active_campaign
ON CONFLICT (campana_id) DO UPDATE SET
    nota = CASE
        WHEN modelo_campana_operativa.nota IS NULL OR modelo_campana_operativa.nota = ''
            THEN EXCLUDED.nota
        WHEN modelo_campana_operativa.nota LIKE '%M-04:%'
            THEN modelo_campana_operativa.nota
        ELSE modelo_campana_operativa.nota || ' ' || EXCLUDED.nota
    END,
    origen_metadato = 'seed_curado',
    estado_metadato = 'curado',
    completeness_estado = EXCLUDED.completeness_estado,
    actualizado_at = now();
