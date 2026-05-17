\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LGT') THEN
        RAISE EXCEPTION 'Missing norma LGT';
    END IF;
END $$;

UPDATE obligacion_perfil
SET norma_codigo = 'LGT',
    articulo_referencia = 'DA 22.ª ap. 1',
    fuente_secundaria = 'RD 1021/2015 (transposición CRS a España)',
    source_url = 'https://sede.agenciatributaria.gob.es/Sede/ayuda/modelos-formularios-presentaciones/modelos-200-299/modelo-289.html',
    verified = true,
    completeness = 'parcial',
    notas = 'CRS - Common Reporting Standard. Base legal LGT disposición adicional 22.ª apartado 1: instituciones financieras deben identificar residencia fiscal y suministrar informacion a la Administracion Tributaria sobre determinadas cuentas financieras. Condicional: aplica si la entidad es Institucion Financiera Obligada segun RD 1021/2015. Verificar clasificacion antes de aplicar.'
WHERE descripcion ILIKE '%Modelo 289%'
  AND verified = false;
