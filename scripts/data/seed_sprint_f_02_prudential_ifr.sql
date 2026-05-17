\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32019R2033') THEN
        RAISE EXCEPTION 'Missing norma 32019R2033; run F-01 first';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32019L2034') THEN
        RAISE EXCEPTION 'Missing norma 32019L2034; run F-01 first';
    END IF;
END $$;

UPDATE obligacion_perfil
SET norma_codigo = '32019R2033',
    articulo_referencia = 'art. 11',
    fuente_secundaria = 'IFD 32019L2034 art. 40+ (transposición supervisión)',
    verified = true,
    completeness = 'completa',
    source_url = 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32019R2033',
    notas = 'ESI sujetas a IFR/IFD desde 26/06/2021. CRR (32013R0575) no aplica como marco prudencial primario para ESI. IFR art. 11: requisito de fondos propios = mayor de capital inicial, GFR (gasto fijo general) o K-factor.'
WHERE descripcion ILIKE '%prudencial%recursos propios%'
  AND perfil_codigo IN ('sociedad_valores', 'agencia_valores');

INSERT INTO obligacion_fuente (
    obligacion_id,
    fuente_tipo,
    codigo_referencia,
    articulo,
    descripcion,
    source_url,
    peso
)
SELECT op.id,
       'norma_primaria',
       '32019R2033',
       'art. 11',
       'IFR art. 11 - requisitos de fondos propios de empresas de servicios de inversion',
       'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32019R2033',
       1
FROM obligacion_perfil op
WHERE op.descripcion ILIKE '%prudencial%recursos propios%'
  AND op.perfil_codigo IN ('sociedad_valores', 'agencia_valores')
  AND NOT EXISTS (
      SELECT 1
      FROM obligacion_fuente ofu
      WHERE ofu.obligacion_id = op.id
        AND ofu.fuente_tipo = 'norma_primaria'
        AND ofu.codigo_referencia = '32019R2033'
        AND ofu.articulo = 'art. 11'
  );
