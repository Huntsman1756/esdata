BEGIN;

UPDATE obligacion_perfil
SET plazo_descripcion = 'Del 1 al 20 de enero, abril, julio y octubre'
WHERE modelo_aeat = '115'
  AND periodicidad = 'trimestral'
  AND plazo_descripcion IS NULL;

UPDATE obligacion_perfil
SET plazo_descripcion = 'Del 1 al 31 de enero del año siguiente (hasta el primer día hábil si procede)'
WHERE modelo_aeat = '296'
  AND periodicidad = 'anual'
  AND plazo_descripcion IS NULL;

DO $$
DECLARE
    missing_count integer;
BEGIN
    SELECT COUNT(*)
    INTO missing_count
    FROM obligacion_perfil
    WHERE periodicidad IN ('mensual', 'trimestral', 'semestral', 'anual')
      AND plazo_descripcion IS NULL;

    IF missing_count <> 0 THEN
        RAISE EXCEPTION 'Periodic obligations still missing plazo_descripcion: %', missing_count;
    END IF;
END $$;

COMMIT;
