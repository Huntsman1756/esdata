\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'RD_1082_2012') THEN
        RAISE EXCEPTION 'Missing norma RD_1082_2012';
    END IF;
END $$;

UPDATE obligacion_perfil
SET norma_codigo = 'RD_1082_2012',
    articulo_referencia = 'art. 150',
    fuente_secundaria = 'Orden HAC/1417/2018 (aprobación Modelo 187)',
    verified = true,
    completeness = 'parcial',
    source_url = 'https://www.boe.es/buscar/act.php?id=BOE-A-2012-9716#a150',
    notas = concat_ws(
        ' ',
        NULLIF(notas, ''),
        'Base legal: RD 1082/2012 art. 150. Obligaciones de informacion sobre ejecucion de ordenes de suscripcion y reembolso de IIC. Modelo 187 condicionado a intervenir en operaciones informables sobre acciones/participaciones de IIC; Orden HAC/1417/2018 aprueba el modelo.'
    )
WHERE perfil_codigo IN ('sociedad_valores', 'agencia_valores', 'sgiic')
  AND descripcion ILIKE '%Modelo 187%';
