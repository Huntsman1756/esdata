\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LIVMC') THEN
        RAISE EXCEPTION 'Missing norma LIVMC';
    END IF;
END $$;

UPDATE obligacion_perfil
SET norma_codigo = 'LIVMC',
    articulo_referencia = 'art. 208 bis',
    fuente_secundaria = '32014L0065 art. 23 (MiFID II)',
    verified = true,
    completeness = 'completa',
    source_url = 'https://www.boe.es/buscar/act.php?id=BOE-A-2015-11435#a2-2',
    notas = 'Articulo confirmado en BOE TRLMV/LIVMC consolidado: art. 208 bis exige organizarse y adoptar medidas para prevenir, detectar y gestionar conflictos de interes entre clientes y la propia empresa o grupo.'
WHERE perfil_codigo IN ('sociedad_valores', 'agencia_valores')
  AND descripcion ILIKE '%conflictos%';

UPDATE obligacion_perfil
SET norma_codigo = 'LIVMC',
    articulo_referencia = 'arts. 221 y 222',
    fuente_secundaria = '32014L0065 art. 27 (MiFID II)',
    verified = true,
    completeness = 'completa',
    source_url = 'https://www.boe.es/buscar/act.php?id=BOE-A-2015-11435#a221',
    notas = CASE
        WHEN perfil_codigo = 'agencia_valores' THEN
            'agencia_valores tiene obligacion de transmision de ordenes; best execution aplica via RTO. No ejecuta directamente (LIVMC art. 144). Articulos confirmados en BOE: LIVMC art. 221 exige mejores resultados al ejecutar ordenes y art. 222 regula la politica de ejecucion.'
        ELSE
            'Articulos confirmados en BOE TRLMV/LIVMC consolidado: art. 221 exige medidas suficientes para obtener el mejor resultado posible en ejecucion de ordenes y art. 222 regula la politica de ejecucion de ordenes.'
    END
WHERE perfil_codigo IN ('sociedad_valores', 'agencia_valores')
  AND descripcion ILIKE '%mejor ejecucion%';
