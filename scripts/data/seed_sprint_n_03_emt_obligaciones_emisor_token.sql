-- N-03: Seed EMT obligations for emisor_token - MiCA Title IV
-- EMT rows are conditional because only credit institutions or e-money institutions may issue EMT.

DO $$
DECLARE
  v_oblig_id INTEGER;
  v_source_url TEXT := 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1114';
BEGIN
  IF NOT EXISTS (SELECT 1 FROM perfil_entidad WHERE codigo = 'emisor_token') THEN
    RAISE EXCEPTION 'N-03: perfil emisor_token not found. Run N-01 first.';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32023R1114') THEN
    RAISE EXCEPTION 'N-03: canonical MiCA norma 32023R1114 not found.';
  END IF;

  -- Art. 48 - EMT issuer eligibility and notification.
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'emisor_token'
      AND norma_codigo = '32023R1114'
      AND articulo_referencia = 'art. 48'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'emisor_token', 'AUTORIZACION',
      'Notificacion BdE para emision de fichas de dinero electronico (EMT)',
      'ad_hoc', NULL, NULL,
      '32023R1114', 'art. 48', NULL,
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'art. 48 MiCA: solo entidades de credito o entidades de dinero electronico pueden emitir EMT. Notificacion a BdE antes de emision; no autorizacion MiCA nueva si ya existe licencia EC/EMI. completeness=parcial: condicional a ser EC o entidad DME.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 48', 'MiCA art. 48 - Requisitos EMT', v_source_url, 3);
  END IF;

  -- Art. 51 - EMT white paper.
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'emisor_token'
      AND norma_codigo = '32023R1114'
      AND articulo_referencia = 'art. 51'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'emisor_token', 'REPORTING',
      'White paper EMT: publicacion y notificacion',
      'ad_hoc', NULL, NULL,
      '32023R1114', 'art. 51', NULL,
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'art. 51 MiCA: white paper EMT obligatorio con contenido mas reducido que ART. Notificacion a BdE y publicacion antes de oferta publica o admision a negociacion. No requiere aprobacion previa ordinaria. completeness=parcial: solo aplica a EC o entidad DME emisora.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 51', 'MiCA art. 51 - White paper EMT', v_source_url, 3);
  END IF;

  -- Art. 55 - redemption at par.
  IF NOT EXISTS (
    SELECT 1 FROM obligacion_perfil
    WHERE perfil_codigo = 'emisor_token'
      AND norma_codigo = '32023R1114'
      AND articulo_referencia = 'art. 55'
  ) THEN
    INSERT INTO obligacion_perfil (
      perfil_codigo, obligacion_tipo, descripcion,
      periodicidad, plazo_descripcion, modelo_aeat,
      norma_codigo, articulo_referencia, fuente_secundaria,
      evidencia_tipo, safe_to_answer, verified, completeness,
      source_url, capture_date, notas
    ) VALUES (
      'emisor_token', 'CONTROL_INTERNO',
      'Derecho de reembolso EMT al valor nominal',
      'continua', NULL, NULL,
      '32023R1114', 'art. 55', NULL,
      NULL, true, true, 'parcial',
      v_source_url, CURRENT_DATE,
      'art. 55 MiCA: derecho de reembolso al valor nominal en cualquier momento para todos los tenedores de EMT. Reembolso sin comision y con fondos mantenidos en deposito o activos seguros liquidos. completeness=parcial: solo aplica a EC o entidad DME emisora.'
    );
    v_oblig_id := currval('obligacion_perfil_id_seq');
    INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
    VALUES (v_oblig_id, 'norma_primaria', '32023R1114', 'art. 55', 'MiCA art. 55 - Reembolso EMT', v_source_url, 3);
  END IF;
END $$;
