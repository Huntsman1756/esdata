-- M-03: Seed base MiCA obligations for casp - arts. 59-76, 81-83, 94
-- All obligations reference MiCA canonical norma 32023R1114
-- Prerequisites: M-01 (canonical norma), M-02 (perfil casp)

DO $$
DECLARE
  v_oblig_id INTEGER;
  v_source_url TEXT := 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1114';
BEGIN
  -- Verify perfil casp exists
  IF NOT EXISTS (SELECT 1 FROM perfil_entidad WHERE codigo = 'casp') THEN
    RAISE EXCEPTION 'M-03: perfil casp not found. Run M-02 first.';
  END IF;

  -- 1. Art. 59 - Autorizaci\u00f3n CNMV como CASP
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'casp' AND norma_codigo = '32023R1114'
    AND articulo_referencia = 'art. 59'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'casp', 'AUTORIZACION',
      'Autorizaci\u00f3n como CASP ante la CNMV antes de prestar cualquier servicio de criptoactivos',
      'continua', NULL, NULL,
      '32023R1114', 'art. 59', NULL,
      NULL, true, true, 'completa',
      v_source_url, CURRENT_DATE,
      'MiCA art. 59: toda entidad que preste servicios de criptoactivos debe obtener autorizaci\u00f3n previa de la autoridad competente (CNMV en Espa\u00f1a). Art. 62 desarrolla la informaci\u00f3n de la solicitud mediante RTS 32025R0305.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 59', 'MiCA art. 59 - Autorizaci\u00f3n CASP', v_source_url, 3);
  END IF;

  -- 2. Art. 62 - Aplicaci\u00f3n autorizaci\u00f3n (informaci\u00f3n solicitud)
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'casp' AND norma_codigo = '32023R1114'
    AND articulo_referencia = 'art. 62'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'casp', 'AUTORIZACION',
      'Informaci\u00f3n de la solicitud de autorizaci\u00f3n CASP seg\u00fan art. 62 y RTS 32025R0305',
      'ad_hoc', NULL, NULL,
      '32023R1114', 'art. 62', '32025R0305',
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'MiCA art. 62: requisitos de la solicitud de autorizaci\u00f3n. Desarrollado por RTS 32025R0305 (solicitud) e ITS 32025R0306 (plantillas).'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 62', 'MiCA art. 62 - Solicitud autorizaci\u00f3n', v_source_url, 3);
  END IF;

  -- 3. Art. 65 - Requisitos de capital
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'casp' AND norma_codigo = '32023R1114'
    AND articulo_referencia = 'art. 65'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'casp', 'CONTROL_INTERNO',
      'Requisitos de capital propio seg\u00fan tipo de servicio CASP prestado',
      'continua', NULL, NULL,
      '32023R1114', 'art. 65', NULL,
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'MiCA art. 65: requisitos de capital propio variables seg\u00fan el tipo de servicio de criptoactivos prestado. M\u00ednimo fijo y adicional por volumen.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 65', 'MiCA art. 65 - Capital propio', v_source_url, 3);
  END IF;

  -- 4. Arts. 66-67 - Gobierno, buena reputaci\u00f3n, conocimiento y experiencia
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'casp' AND norma_codigo = '32023R1114'
    AND (articulo_referencia = 'art. 66' OR articulo_referencia = 'art. 67')
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'casp', 'CONTROL_INTERNO',
      'Gobierno corporativo, buena reputaci\u00f3n y experiencia de los administradores (arts. 66-67 fit and proper)',
      'continua', NULL, NULL,
      '32023R1114', 'art. 66', NULL,
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'MiCA arts. 66-67: gobierno corporativo s\u00f3lido, administradores con buena reputaci\u00f3n y conocimientos/experiencia suficientes para prestar servicios CASP.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'arts. 66-67', 'MiCA arts. 66-67 - Gobierno y fit & proper', v_source_url, 3);
  END IF;

  -- 5. Art. 70 - Custodia y segregaci\u00f3n de activos de clientes
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'casp' AND norma_codigo = '32023R1114'
    AND articulo_referencia = 'art. 70'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'casp', 'CONTROL_INTERNO',
      'Custodia de criptoactivos y segregaci\u00f3n de activos de clientes',
      'continua', NULL, NULL,
      '32023R1114', 'art. 70', NULL,
      NULL, true, true, 'completa',
      v_source_url, CURRENT_DATE,
      'MiCA art. 70: los CASP deben segreg\u00e1r los criptoactivos de clientes de los propios, con requisitos estrictos de custodia y protecci\u00f3n.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 70', 'MiCA art. 70 - Custodia y segregaci\u00f3n', v_source_url, 3);
  END IF;

  -- 6. Art. 81 - Continuidad y regularidad (desarrollado por RTS 32025R0299)
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'casp' AND norma_codigo = '32023R1114'
    AND articulo_referencia = 'art. 81'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'casp', 'CONTROL_INTERNO',
      'Continuidad y regularidad de los servicios de criptoactivos',
      'continua', NULL, NULL,
      '32023R1114', 'art. 81', '32025R0299',
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'MiCA art. 81: los CASP deben garantizar la continuidad y regularidad de los servicios. Desarrollado por RTS 32025R0299 (continuidad y regularidad).'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 81', 'MiCA art. 81 - Continuidad y regularidad', v_source_url, 3);
  END IF;

  -- 7. Arts. 72-73 - Reclamaciones y conflictos de inter\u00e9s
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'casp' AND norma_codigo = '32023R1114'
    AND (articulo_referencia = 'art. 72' OR articulo_referencia = 'art. 73')
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'casp', 'CONTROL_INTERNO',
      'Mecanismo de reclamaciones de clientes y gesti\u00f3n de conflictos de inter\u00e9s',
      'continua', NULL, NULL,
      '32023R1114', 'art. 72', NULL,
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'MiCA arts. 72-73: mecanismo de reclamaciones accesible para clientes (art. 72) y pol\u00edtica de gesti\u00f3n de conflictos de inter\u00e9s (art. 73).'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'arts. 72-73', 'MiCA arts. 72-73 - Reclamaciones y conflictos', v_source_url, 3);
  END IF;

  -- 8. Art. 94 - PBC/FT por referencia al marco AML
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'casp' AND norma_codigo = '32023R1114'
    AND articulo_referencia = 'art. 94'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'casp', 'PBC_FT',
      'Obligaciones PBC/FT por referencia al marco antilavado (art. 94 MiCA)',
      'continua', NULL, NULL,
      '32023R1114', 'art. 94', NULL,
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'MiCA art. 94: los CASP est\u00e1n sujetos a obligaciones PBC/FT por referencia al marco AML de la UE (Directiva 5AMLD/6AMLD y Reglamento UE 2015/847). Las obligaciones concretas de PBC en Espa\u00f1a se definen en Ley 10/2010 y normativa SEPBLAC, no directamente en MiCA.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 94', 'MiCA art. 94 - PBC/FT referencia AML', v_source_url, 3);
  END IF;

END $$;
