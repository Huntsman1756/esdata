\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LGT') THEN
        RAISE EXCEPTION 'Missing norma LGT';
    END IF;
END $$;

UPDATE obligacion_perfil
SET norma_codigo = 'LGT',
    articulo_referencia = 'art. 93',
    fuente_secundaria = 'Orden EHA/3895/2004 (aprobación Modelo 198)',
    source_url = 'https://sede.agenciatributaria.gob.es/Sede/ayuda/modelos-formularios-presentaciones/modelos-100-199/modelo-198.html',
    verified = true,
    completeness = 'parcial',
    notas = 'Obligacion de declarar operaciones con activos financieros y valores mobiliarios. Base legal LGT art. 93: obligacion de proporcionar a la Administracion tributaria datos con trascendencia tributaria deducidos de relaciones economicas, profesionales o financieras. Condicional: solo si hay operaciones informables en el ejercicio.'
WHERE descripcion ILIKE '%Modelo 198%'
  AND verified = false;
