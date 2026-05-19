-- M-01: Replace MICA_2023_1114 with canonical 32023R1114
-- MiCA - Reglamento (UE) 2023/1114 del Parlamento Europeo y del Consejo
-- de 31 de mayo de 2023 relativo a los criptoactivos

DO $$
BEGIN
  -- Delete weak MICA_2023_1114 row if it exists
  DELETE FROM obligacion_perfil WHERE norma_codigo = 'MICA_2023_1114';
  DELETE FROM obligacion_fuente WHERE obligacion_id IN (
    SELECT id FROM obligacion_perfil WHERE norma_codigo = 'MICA_2023_1114'
  );
  DELETE FROM norma WHERE codigo = 'MICA_2023_1114';

  -- Insert canonical MiCA regulation if not exists
  IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32023R1114') THEN
    INSERT INTO norma (
      codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
      tipo_documento, ambito, estado_cobertura, vigente_desde,
      celex, tipo_norma, publicacion_doue, url_eurlex, vigente,
      norma_padre_celex
    ) VALUES (
      '32023R1114',
      'Reglamento (UE) 2023/1114 del Parlamento Europeo y del Consejo, de 31 de mayo de 2023, relativo a los criptoactivos y que modifica y deroga la Directiva (UE) 2019/1937 (MiCA)',
      'BOE-A-2023-12793',
      'eli/reg/2023/1114/spa',
      'UE',
      'eurlex',
      'reglamento_ue',
      'mercado_interior',
      'complete',
      '2023-05-31'::date,
      '32023R1114',
      'reglamento_ue',
      '2023-06-09'::date,
      'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1114',
      true,
      NULL
    );
  END IF;
END $$;
