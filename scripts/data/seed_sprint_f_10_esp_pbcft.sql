\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LEY10_2010') THEN
        RAISE EXCEPTION 'Missing norma LEY10_2010';
    END IF;
END $$;

UPDATE obligacion_perfil
SET norma_codigo = 'LEY10_2010',
    articulo_referencia = 'art. 2.1.h',
    verified = true,
    completeness = 'parcial',
    source_url = 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737#a2',
    notas = 'Empresa de servicios de pago es sujeto obligado segun LEY10_2010 art. 2.1.h. Obligacion legal confirmada; aplicacion operativa condicionada por actividad, servicios prestados y umbrales/reglas de desarrollo en RD_304_2014.'
WHERE id = 131
  AND perfil_codigo = 'empresa_servicios_pago'
  AND descripcion ILIKE '%PBC/FT%';

DELETE FROM obligacion_fuente
WHERE obligacion_id = 131
  AND codigo_referencia = 'LEY10_2010'
  AND articulo = 'art. 2.1';

INSERT INTO obligacion_fuente (
    obligacion_id,
    fuente_tipo,
    codigo_referencia,
    articulo,
    source_url,
    peso
)
SELECT
    131,
    'norma_primaria',
    'LEY10_2010',
    'art. 2.1.h',
    'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737#a2',
    1
WHERE EXISTS (
    SELECT 1
    FROM obligacion_perfil
    WHERE id = 131
      AND perfil_codigo = 'empresa_servicios_pago'
)
AND NOT EXISTS (
    SELECT 1
    FROM obligacion_fuente
    WHERE obligacion_id = 131
      AND codigo_referencia = 'LEY10_2010'
      AND articulo = 'art. 2.1.h'
);
