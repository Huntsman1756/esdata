ALTER TABLE norma ADD COLUMN IF NOT EXISTS tipo_documento TEXT;
ALTER TABLE norma ADD COLUMN IF NOT EXISTS estado_cobertura TEXT;

UPDATE norma
SET tipo_documento = CASE codigo
    WHEN 'LGT' THEN 'ley'
    WHEN 'LIRPF' THEN 'ley'
    WHEN 'LIS' THEN 'ley'
    WHEN 'LIVA' THEN 'ley'
    ELSE 'ley'
END
WHERE tipo_documento IS NULL;

UPDATE norma
SET ambito = CASE
    WHEN ambito = 'fiscal' THEN 'tributario'
    ELSE ambito
END;

UPDATE norma
SET estado_cobertura = 'ingestada'
WHERE estado_cobertura IS NULL;

ALTER TABLE norma ALTER COLUMN tipo_documento SET NOT NULL;
ALTER TABLE norma ALTER COLUMN estado_cobertura SET NOT NULL;
