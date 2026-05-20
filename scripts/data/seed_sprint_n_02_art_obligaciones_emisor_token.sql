-- N-02: Seed ART obligations for emisor_token - MiCA Title III
-- Prerequisites: canonical norma 32023R1114 and perfil emisor_token.

DO $$
DECLARE
  v_oblig_id INTEGER;
  v_source_url TEXT := 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1114';
BEGIN
  IF NOT EXISTS (SELECT 1 FROM perfil_entidad WHERE codigo = 'emisor_token') THEN
    RAISE EXCEPTION 'N-02: perfil emisor_token not found. Run N-01 first.';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32023R1114') THEN
    RAISE EXCEPTION 'N-02: canonical MiCA norma 32023R1114 not found.';
  END IF;

  -- Art. 18 - ART authorization.
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'emisor_token'
      AND norma_codigo = '32023R1114'
      AND articulo_referencia = 'art. 18'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'emisor_token', 'AUTORIZACION',
      'Autorizacion CNMV para emitir fichas referenciadas a activos (ART)',
      'ad_hoc', NULL, NULL,
      '32023R1114', 'art. 18', NULL,
      NULL, true, true, 'completa',
      v_source_url, CURRENT_DATE,
      'art. 18 MiCA: autorizacion CNMV obligatoria antes de emitir ART. Excepcion: entidades de credito pueden emitir bajo regimen simplificado del art. 17. Supervisor: CNMV; BdE participa si el ART es significativo. ART significativo: mas de 10M holders o mas de 5B EUR de reserva media.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 18', 'MiCA art. 18 - Autorizacion ART', v_source_url, 3);
  END IF;

  -- Art. 19, with publication context from art. 22.
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'emisor_token'
      AND norma_codigo = '32023R1114'
      AND articulo_referencia = 'art. 19'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'emisor_token', 'REPORTING',
      'White paper ART: contenido minimo, notificacion y publicacion',
      'ad_hoc', NULL, NULL,
      '32023R1114', 'art. 19', NULL,
      NULL, true, true, 'completa',
      v_source_url, CURRENT_DATE,
      'arts. 19-22 MiCA: white paper obligatorio antes de oferta publica o admision a negociacion de ART. Contenido minimo en art. 19. Publicacion en la web del emisor y notificacion a CNMV; no aprobacion previa ordinaria del white paper.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'arts. 19-22', 'MiCA arts. 19-22 - White paper ART', v_source_url, 3);
  END IF;

  -- Art. 35, with custody context from art. 36.
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'emisor_token'
      AND norma_codigo = '32023R1114'
      AND articulo_referencia = 'art. 35'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'emisor_token', 'CONTROL_INTERNO',
      'Reserva de activos y custodia segregada para ART',
      'continua', NULL, NULL,
      '32023R1114', 'art. 35', NULL,
      NULL, true, true, 'completa',
      v_source_url, CURRENT_DATE,
      'arts. 35-36 MiCA: reserva de activos obligatoria para respaldar ART en circulacion. Custodia por entidad de credito o CASP autorizado, con segregacion de activos de reserva. Composicion y gestion sujetas a RTS ESMA/EBA cuando proceda.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'arts. 35-36', 'MiCA arts. 35-36 - Reserva ART', v_source_url, 3);
  END IF;

  -- Art. 25 - ongoing issuer obligations.
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'emisor_token'
      AND norma_codigo = '32023R1114'
      AND articulo_referencia = 'art. 25'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'emisor_token', 'CONTROL_INTERNO',
      'Obligaciones continuas del emisor ART',
      'continua', NULL, NULL,
      '32023R1114', 'art. 25', NULL,
      NULL, true, true, 'completa',
      v_source_url, CURRENT_DATE,
      'art. 25 MiCA: obligaciones continuas del emisor ART, incluyendo capital minimo, politicas de gobernanza, informacion periodica a la autoridad competente, politica de reclamaciones y gestion de conflictos de interes.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 25', 'MiCA art. 25 - Obligaciones continuas ART', v_source_url, 3);
  END IF;

  -- Art. 45 - significant ART restrictions.
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'emisor_token'
      AND norma_codigo = '32023R1114'
      AND articulo_referencia = 'art. 45'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'emisor_token', 'CONTROL_INTERNO',
      'Restricciones y obligaciones adicionales para ART significativo',
      'continua', NULL, NULL,
      '32023R1114', 'art. 45', NULL,
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'art. 45 MiCA: si el ART es clasificado como significativo por ESMA/EBA, aplican obligaciones adicionales, supervision reforzada CNMV/BdE, limites y reporting reforzado. completeness=parcial: condicional a clasificacion como significativo.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 45', 'MiCA art. 45 - ART significativo', v_source_url, 3);
  END IF;
END $$;
