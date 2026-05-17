\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32011L0061') THEN
        RAISE EXCEPTION 'Missing norma 32011L0061';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'RD_1082_2012') THEN
        RAISE EXCEPTION 'Missing norma RD_1082_2012';
    END IF;
END $$;

-- Consolidate duplicate AIFMD Annex IV obligations: keep id 73, remove id 133.
DELETE FROM obligacion_fuente
WHERE obligacion_id = 133
  AND EXISTS (
      SELECT 1
      FROM obligacion_fuente kept
      WHERE kept.obligacion_id = 73
        AND kept.codigo_referencia = obligacion_fuente.codigo_referencia
        AND COALESCE(kept.articulo, '') = COALESCE(obligacion_fuente.articulo, '')
  );

UPDATE obligacion_fuente
SET obligacion_id = 73
WHERE obligacion_id = 133;

UPDATE obligacion_perfil
SET descripcion = 'Reporte AIFMD Annex IV a CNMV - activos bajo gestion',
    norma_codigo = '32011L0061',
    articulo_referencia = 'art. 24 + Annex IV',
    periodicidad = 'trimestral',
    plazo_descripcion = 'Trimestral si AUM > 500M EUR; semestral si AUM 100-500M EUR',
    verified = true,
    completeness = 'parcial',
    source_url = 'https://eur-lex.europa.eu/legal-content/ES/ALL/?uri=celex:32011L0061',
    notas = 'AIFMD Annex IV reporting. Base confirmada: AIFMD art. 24 exige informacion periodica a autoridades competentes; Reglamento Delegado (UE) 231/2013 Annex IV contiene la plantilla de reporting. Umbral operativo: AUM > 100M EUR (apalancado) o > 500M EUR (sin apalancamiento). Formularios CNMV segun circular vigente.'
WHERE id = 73;

DELETE FROM obligacion_perfil
WHERE id = 133;

UPDATE obligacion_perfil
SET articulo_referencia = 'art. 16',
    verified = true,
    completeness = 'parcial',
    fuente_secundaria = 'ESMA34-39-897 + ESMA34-671404336-1364',
    source_url = 'https://eur-lex.europa.eu/legal-content/ES/ALL/?uri=celex:32011L0061',
    notas = 'AIFMD art. 16 confirmado: gestion de liquidez y pruebas de esfuerzo periodicas en condiciones normales y excepcionales. Obligacion condicional al tipo de IIC/FIA y requerimientos CNMV/ESMA aplicables.'
WHERE id = 75;

UPDATE obligacion_perfil
SET articulo_referencia = 'art. 16',
    verified = true,
    completeness = 'parcial',
    fuente_secundaria = 'ESMA34-671404336-1364 liquidity management tools guidance',
    source_url = 'https://eur-lex.europa.eu/legal-content/ES/ALL/?uri=celex:32011L0061',
    notas = 'AIFMD art. 16 confirmado: gestion de liquidez. Reporting de herramientas de gestion de liquidez condicionado a requerimientos CNMV/ESMA y al regimen aplicable tras AIFMD/UCITS liquidity management tools.'
WHERE id = 137;

UPDATE obligacion_perfil
SET norma_codigo = 'RD_1082_2012',
    articulo_referencia = 'art. 22',
    verified = true,
    completeness = 'parcial',
    source_url = 'https://www.boe.es/buscar/act.php?id=BOE-A-2012-9716#a22',
    notas = 'RD 1082/2012 art. 22 confirmado: la SGIIC, para cada fondo que administre, y las sociedades de inversion deben publicar informe anual y semestral; CNMV puede exigir informacion periodica adicional, forma, contenido y plazos. Periodicidad/formato concreto queda condicionado a circular CNMV vigente.'
WHERE id = 70;
