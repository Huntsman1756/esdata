\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LGT') THEN
        RAISE EXCEPTION 'Missing norma LGT';
    END IF;
END $$;

UPDATE obligacion_perfil
SET norma_codigo = 'LGT',
    articulo_referencia = 'DA 22.ª ap. 8',
    fuente_secundaria = 'RD 1021/2015 art. 3 (FATCA en España)',
    source_url = 'https://sede.agenciatributaria.gob.es/Sede/ayuda/modelos-formularios-presentaciones/modelos-200-299/modelo-290.html',
    verified = true,
    completeness = 'parcial',
    notas = 'FATCA. Base legal LGT disposicion adicional 22.ª apartado 8: aplica las obligaciones de informacion y diligencia debida de cuentas financieras al Acuerdo entre Estados Unidos y España para implementar FATCA. Condicional: aplica si la entidad tiene cuentas de US persons o passive NFFE con substantial US owner. Ver modelo_regla_inclusion para reglas de clasificacion.'
WHERE descripcion ILIKE '%Modelo 290%'
  AND verified = false;
