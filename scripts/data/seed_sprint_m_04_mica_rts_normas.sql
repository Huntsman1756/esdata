-- M-04: Load 3 MiCA RTS/ITS for CASP (32025R0305, 32025R0299, 32025R0306)
-- All verified via EUR-Lex HTTP 200 + content match (2023/1114, criptoactivos, CASP)

-- 32025R0305 - RTS solicitud autorizaci\u00f3n CASP (art. 62)
-- 32025R0299 - RTS continuidad y regularidad (art. 81)
-- 32025R0306 - ITS plantillas solicitud autorizaci\u00f3n CASP (art. 62)

DO $$
DECLARE
  v_source_url TEXT := 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:';
BEGIN
  -- 32025R0305 - RTS solicitud autorizaci\u00f3n CASP, art. 62
  IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32025R0305') THEN
    INSERT INTO norma (
      codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
      tipo_documento, ambito, estado_cobertura, vigente_desde,
      celex, tipo_norma, publicacion_doue, url_eurlex, vigente,
      norma_padre_celex
    ) VALUES (
      '32025R0305',
      'Reglamento Delegado (UE) 2025/305 de la Comisi\u00f3n, de 21 de diciembre de 2024, que completa el Reglamento (UE) 2023/1114 del Parlamento Europeo y del Consejo en lo que respecta a normas t\u00e9cnicas de regulaci\u00f3n sobre los requisitos y procedimientos para la solicitud de autorizaci\u00f3n de los proveedores de servicios de criptoactivos',
      'BOE-A-2025-2680',
      'eli/reg_del/2025/305/spa',
      'UE',
      'eurlex',
      'reglamento_delegado_ue',
      'mercado_interior',
      'complete',
      '2024-12-21'::date,
      '32025R0305',
      'reglamento_delegado_ue',
      '2025-02-08'::date,
      'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32025R0305',
      true,
      '32023R1114'
    );
  END IF;

  -- 32025R0299 - RTS continuidad y regularidad, art. 81
  IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32025R0299') THEN
    INSERT INTO norma (
      codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
      tipo_documento, ambito, estado_cobertura, vigente_desde,
      celex, tipo_norma, publicacion_doue, url_eurlex, vigente,
      norma_padre_celex
    ) VALUES (
      '32025R0299',
      'Reglamento Delegado (UE) 2025/299 de la Comisi\u00f3n, de 21 de diciembre de 2024, que completa el Reglamento (UE) 2023/1114 del Parlamento Europeo y del Consejo en lo que respecta a normas t\u00e9cnicas de regulaci\u00f3n sobre los requisitos de continuidad y regularidad de los proveedores de servicios de criptoactivos',
      'BOE-A-2025-2678',
      'eli/reg_del/2025/299/spa',
      'UE',
      'eurlex',
      'reglamento_delegado_ue',
      'mercado_interior',
      'complete',
      '2024-12-21'::date,
      '32025R0299',
      'reglamento_delegado_ue',
      '2025-02-08'::date,
      'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32025R0299',
      true,
      '32023R1114'
    );
  END IF;

  -- 32025R0306 - ITS plantillas solicitud autorizaci\u00f3n, art. 62
  IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32025R0306') THEN
    INSERT INTO norma (
      codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
      tipo_documento, ambito, estado_cobertura, vigente_desde,
      celex, tipo_norma, publicacion_doue, url_eurlex, vigente,
      norma_padre_celex
    ) VALUES (
      '32025R0306',
      'Reglamento de Ejecuci\u00f3n (UE) 2025/306 de la Comisi\u00f3n, de 21 de diciembre de 2024, por el que establecen modelos normalizados de formularios, informes y solicitudes para la solicitud de autorizaci\u00f3n de los proveedores de servicios de criptoactivos, y por el que se modifican los anexos I y II del Reglamento de Ejecuci\u00f3n (UE) 2018/623',
      'BOE-A-2025-2681',
      'eli/reg_ejec/2025/306/spa',
      'UE',
      'eurlex',
      'reglamento_delegado_ue',
      'mercado_interior',
      'complete',
      '2024-12-21'::date,
      '32025R0306',
      'reglamento_delegado_ue',
      '2025-02-08'::date,
      'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32025R0306',
      true,
      '32023R1114'
    );
  END IF;
END $$;
