-- Sprint E seed: complete applicability profiles.
-- Scope: eaf, entidad_credito, empresa_servicios_pago, sgiic additions, agencia_valores verification upgrade.
-- Safe to rerun: obligations are upserted and their generated source rows are refreshed.

BEGIN;

DO $$
DECLARE
    missing_profiles TEXT;
    missing_norms TEXT;
BEGIN
    SELECT string_agg(codigo, ', ' ORDER BY codigo)
    INTO missing_profiles
    FROM (
        VALUES
            ('eaf'), ('entidad_credito'), ('empresa_servicios_pago'),
            ('sgiic'), ('agencia_valores')
    ) AS required(codigo)
    WHERE NOT EXISTS (SELECT 1 FROM perfil_entidad pe WHERE pe.codigo = required.codigo);

    IF missing_profiles IS NOT NULL THEN
        RAISE EXCEPTION 'Missing perfil_entidad rows: %', missing_profiles;
    END IF;

    SELECT string_agg(codigo, ', ' ORDER BY codigo)
    INTO missing_norms
    FROM (
        VALUES
            ('LIRPF'), ('LIVA'), ('LIS'), ('TRLIRNR'), ('LEY10_2010'),
            ('RD_304_2014'), ('LIVMC'), ('RD_1082_2012'), ('32014L0065'),
            ('32013R0575'), ('32022R2554'), ('32015L2366'),
            ('LEY10_2014'), ('RD19_2018'), ('32011L0061'), ('32009L0065')
    ) AS required(codigo)
    WHERE NOT EXISTS (SELECT 1 FROM norma n WHERE n.codigo = required.codigo);

    IF missing_norms IS NOT NULL THEN
        RAISE EXCEPTION 'Missing required norma rows: %', missing_norms;
    END IF;
END
$$;

CREATE TEMP TABLE tmp_modelo_source AS
SELECT
    m.codigo,
    COALESCE(c.url_instrucciones, m.url_info, c.url_normativa) AS source_url
FROM aeat_modelo m
LEFT JOIN modelo_campana c
    ON c.modelo_id = m.id
   AND c.activo = true
WHERE m.codigo IN ('111', '115', '187', '193', '196', '198', '200', '216', '289', '290', '296', '303');

DO $$
DECLARE
    missing_models TEXT;
BEGIN
    SELECT string_agg(codigo, ', ' ORDER BY codigo)
    INTO missing_models
    FROM (
        VALUES ('111'), ('115'), ('187'), ('193'), ('196'), ('198'),
               ('200'), ('216'), ('289'), ('290'), ('296'), ('303')
    ) AS required(codigo)
    WHERE NOT EXISTS (
        SELECT 1
        FROM tmp_modelo_source source
        WHERE source.codigo = required.codigo
          AND source.source_url IS NOT NULL
          AND source.source_url <> ''
    );

    IF missing_models IS NOT NULL THEN
        RAISE EXCEPTION 'Missing AEAT source URLs for models: %', missing_models;
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION pg_temp.source_url_for_model(model_code TEXT)
RETURNS TEXT AS $$
DECLARE
    found_url TEXT;
BEGIN
    SELECT source_url INTO found_url
    FROM tmp_modelo_source
    WHERE codigo = model_code;
    IF found_url IS NULL OR found_url = '' THEN
        RAISE EXCEPTION 'Missing source URL for AEAT model %', model_code;
    END IF;
    RETURN found_url;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.seed_obligacion(
    p_perfil TEXT,
    p_tipo TEXT,
    p_descripcion TEXT,
    p_periodicidad TEXT,
    p_plazo TEXT,
    p_modelo TEXT,
    p_norma TEXT,
    p_articulo TEXT,
    p_fuente_secundaria TEXT,
    p_evidencia_tipo TEXT,
    p_verified BOOLEAN,
    p_completeness TEXT,
    p_source_url TEXT,
    p_notas TEXT,
    p_fuente_tipo TEXT DEFAULT 'norma_primaria',
    p_fuente_codigo TEXT DEFAULT NULL,
    p_fuente_articulo TEXT DEFAULT NULL,
    p_fuente_url TEXT DEFAULT NULL,
    p_fuente_peso INTEGER DEFAULT 1
) RETURNS INTEGER AS $$
DECLARE
    row_id INTEGER;
BEGIN
    IF p_source_url IS NULL OR p_source_url = '' THEN
        RAISE EXCEPTION 'source_url is mandatory for obligation %.%', p_perfil, p_descripcion;
    END IF;

    INSERT INTO obligacion_perfil (
        perfil_codigo,
        obligacion_tipo,
        descripcion,
        periodicidad,
        plazo_descripcion,
        modelo_aeat,
        norma_codigo,
        articulo_referencia,
        fuente_secundaria,
        evidencia_tipo,
        safe_to_answer,
        verified,
        completeness,
        source_url,
        capture_date,
        notas
    ) VALUES (
        p_perfil,
        p_tipo,
        p_descripcion,
        p_periodicidad,
        p_plazo,
        p_modelo,
        p_norma,
        p_articulo,
        p_fuente_secundaria,
        p_evidencia_tipo,
        true,
        p_verified,
        p_completeness,
        p_source_url,
        CURRENT_DATE,
        p_notas
    )
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion) DO UPDATE SET
        periodicidad = EXCLUDED.periodicidad,
        plazo_descripcion = EXCLUDED.plazo_descripcion,
        modelo_aeat = EXCLUDED.modelo_aeat,
        norma_codigo = EXCLUDED.norma_codigo,
        articulo_referencia = EXCLUDED.articulo_referencia,
        fuente_secundaria = EXCLUDED.fuente_secundaria,
        evidencia_tipo = EXCLUDED.evidencia_tipo,
        safe_to_answer = EXCLUDED.safe_to_answer,
        verified = EXCLUDED.verified,
        completeness = EXCLUDED.completeness,
        source_url = EXCLUDED.source_url,
        capture_date = EXCLUDED.capture_date,
        notas = EXCLUDED.notas
    RETURNING id INTO row_id;

    DELETE FROM obligacion_fuente WHERE obligacion_id = row_id;

    IF COALESCE(p_fuente_codigo, p_norma) IS NOT NULL AND COALESCE(p_fuente_url, p_source_url) IS NOT NULL THEN
        INSERT INTO obligacion_fuente (
            obligacion_id,
            fuente_tipo,
            codigo_referencia,
            articulo,
            descripcion,
            source_url,
            peso
        ) VALUES (
            row_id,
            p_fuente_tipo,
            COALESCE(p_fuente_codigo, p_norma),
            COALESCE(p_fuente_articulo, p_articulo),
            p_descripcion,
            COALESCE(p_fuente_url, p_source_url),
            p_fuente_peso
        );
    END IF;

    RETURN row_id;
END;
$$ LANGUAGE plpgsql;

-- EAF fiscal obligations.
DO $$
BEGIN
    PERFORM pg_temp.seed_obligacion('eaf', 'AUTOLIQUIDACION', 'Modelo 111 - Retenciones trabajo y actividades profesionales', 'trimestral', 'mensual o trimestral segun volumen y condiciones AEAT', '111', 'LIRPF', 'art. 101', 'AEAT modelo 111', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('111'), 'EAF con empleados o profesionales sujetos a retencion.', 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'AUTOLIQUIDACION', 'Modelo 115 - Retenciones por arrendamientos urbanos', 'trimestral', NULL, '115', 'LIRPF', 'art. 101', 'AEAT modelo 115', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('115'), 'EAF arrendataria de inmueble urbano sujeto a retencion.', 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'AUTOLIQUIDACION', 'Modelo 303 - IVA autoliquidacion', 'trimestral', 'trimestral salvo gran empresa u otros supuestos AEAT', '303', 'LIVA', 'art. 164', 'AEAT modelo 303', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('303'), 'EAF: asesoramiento financiero sujeto a IVA; no se trata como ejecucion/custodia exenta.', 'norma_primaria', 'LIVA', 'art. 164', 'https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'AUTOLIQUIDACION', 'Modelo 200 - Impuesto sobre Sociedades declaracion anual', 'anual', '25 dias naturales siguientes a los 6 meses posteriores al cierre', '200', 'LIS', 'art. 124', 'AEAT modelo 200', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('200'), NULL, 'norma_primaria', 'LIS', 'art. 124', 'https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'DECLARACION_INFORMATIVA', 'Modelo 193 - Retenciones capital mobiliario', 'anual', 'enero', '193', 'LIRPF', 'art. 101', 'AEAT modelo 193', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('193'), NULL, 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'DECLARACION_INFORMATIVA', 'Modelo 198 - Operaciones con activos financieros y valores', 'anual', 'enero-febrero', '198', NULL, NULL, 'AEAT modelo 198', 'norma_primaria', false, 'parcial', pg_temp.source_url_for_model('198'), 'Aplicabilidad condicionada a operaciones informables; norma/articulo especifico pendiente.', 'norma_primaria', 'AEAT_198', NULL, pg_temp.source_url_for_model('198'), 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'DECLARACION_INFORMATIVA', 'Modelo 289 - CRS cuentas financieras', 'anual', 'enero', '289', 'LGT', NULL, 'AEAT modelo 289', 'norma_primaria', false, 'parcial', pg_temp.source_url_for_model('289'), 'Solo si la EAF queda clasificada como institucion financiera obligada CRS.', 'norma_primaria', 'AEAT_289', NULL, pg_temp.source_url_for_model('289'), 1);
END
$$;

-- PBC/FT: EAF shares the same base duties as ESI.
INSERT INTO obligacion_perfil (
    perfil_codigo, obligacion_tipo, descripcion, periodicidad, plazo_descripcion,
    modelo_aeat, norma_codigo, articulo_referencia, fuente_secundaria,
    evidencia_tipo, safe_to_answer, verified, completeness, source_url,
    capture_date, notas
)
SELECT
    'eaf',
    obligacion_tipo,
    descripcion,
    periodicidad,
    plazo_descripcion,
    modelo_aeat,
    norma_codigo,
    articulo_referencia,
    fuente_secundaria,
    evidencia_tipo,
    safe_to_answer,
    verified,
    completeness,
    'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737',
    CURRENT_DATE,
    concat_ws(' ', notas, 'Perfil EAF: sujeto obligado PBC/FT como empresa de servicios de inversion; sin ejecucion ni custodia.')
FROM obligacion_perfil
WHERE perfil_codigo = 'sociedad_valores'
  AND norma_codigo = 'LEY10_2010'
ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion) DO UPDATE SET
    periodicidad = EXCLUDED.periodicidad,
    plazo_descripcion = EXCLUDED.plazo_descripcion,
    norma_codigo = EXCLUDED.norma_codigo,
    articulo_referencia = EXCLUDED.articulo_referencia,
    fuente_secundaria = EXCLUDED.fuente_secundaria,
    evidencia_tipo = EXCLUDED.evidencia_tipo,
    verified = EXCLUDED.verified,
    completeness = EXCLUDED.completeness,
    source_url = EXCLUDED.source_url,
    capture_date = EXCLUDED.capture_date,
    notas = EXCLUDED.notas;

DELETE FROM obligacion_fuente fuente
USING obligacion_perfil obligacion
WHERE fuente.obligacion_id = obligacion.id
  AND obligacion.perfil_codigo = 'eaf'
  AND obligacion.norma_codigo = 'LEY10_2010';

INSERT INTO obligacion_fuente (obligacion_id, fuente_tipo, codigo_referencia, articulo, descripcion, source_url, peso)
SELECT id, 'norma_primaria', 'LEY10_2010', split_part(articulo_referencia, ';', 1), descripcion, 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 1
FROM obligacion_perfil
WHERE perfil_codigo = 'eaf'
  AND norma_codigo = 'LEY10_2010';

-- EAF CNMV/MiFID obligations. Deliberately no MiFIR transaction reporting or best execution.
DO $$
BEGIN
    PERFORM pg_temp.seed_obligacion('eaf', 'CONTROL_INTERNO', 'Politica de conflictos de interes', 'anual', 'Revision anual y cuando cambie el mapa de conflictos', NULL, '32014L0065', 'art. 23', 'MiFID II', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065', 'EAF presta asesoramiento y debe gestionar conflictos de interes.', 'directiva_ue', '32014L0065', 'art. 23', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'CONTROL_INTERNO', 'Evaluacion de idoneidad del cliente', 'continua', 'En cada recomendacion de inversion', NULL, '32014L0065', 'art. 25', 'MiFID II', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065', 'Obligacion nuclear de asesoramiento de inversiones.', 'directiva_ue', '32014L0065', 'art. 25', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'CONTROL_INTERNO', 'Politica de product governance', 'anual', 'Revision anual del mercado objetivo y distribucion', NULL, '32014L0065', 'arts. 16 y 24', 'ESMA35-43-3448', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065', 'Aplicable cuando asesora o distribuye instrumentos financieros.', 'directiva_ue', '32014L0065', 'arts. 16 y 24', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'REPORTING', 'Informacion financiera periodica a CNMV', 'anual', 'Requisitos reducidos aplicables a EAF', NULL, 'LIVMC', 'art. 228', 'CNMV EAF', 'norma_primaria', true, 'parcial', 'https://www.boe.es/buscar/act.php?id=BOE-A-2023-7053', 'Alcance exacto depende del regimen de informacion periodica aplicable a la EAF.', 'norma_primaria', 'LIVMC', 'art. 228', 'https://www.boe.es/buscar/act.php?id=BOE-A-2023-7053', 1);
    PERFORM pg_temp.seed_obligacion('eaf', 'FORMACION', 'Certificacion MiFID II del personal que presta asesoramiento', 'continua', 'Verificacion en contratacion y revision durante la prestacion', NULL, '32014L0065', 'art. 25', 'MiFID II conocimientos y competencia', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065', 'Aplica al personal que asesora o informa sobre instrumentos financieros.', 'directiva_ue', '32014L0065', 'art. 25', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065', 1);
END
$$;

-- Entidad de credito fiscal obligations.
DO $$
BEGIN
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'AUTOLIQUIDACION', 'Modelo 111 - Retenciones trabajo y actividades profesionales', 'mensual', 'mensual o trimestral segun volumen y condiciones AEAT', '111', 'LIRPF', 'art. 101', 'AEAT modelo 111', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('111'), NULL, 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'AUTOLIQUIDACION', 'Modelo 115 - Retenciones por arrendamientos urbanos', 'trimestral', NULL, '115', 'LIRPF', 'art. 101', 'AEAT modelo 115', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('115'), NULL, 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'AUTOLIQUIDACION', 'Modelo 303 - IVA autoliquidacion', 'mensual', 'mensual o trimestral segun volumen y condiciones AEAT', '303', 'LIVA', 'art. 164', 'AEAT modelo 303', 'norma_primaria', true, 'parcial', pg_temp.source_url_for_model('303'), 'Entidad de credito con operaciones exentas y gravadas; revisar actividad concreta.', 'norma_primaria', 'LIVA', 'art. 164', 'https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'AUTOLIQUIDACION', 'Modelo 200 - Impuesto sobre Sociedades declaracion anual', 'anual', '25 dias naturales siguientes a los 6 meses posteriores al cierre', '200', 'LIS', 'art. 124', 'AEAT modelo 200', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('200'), NULL, 'norma_primaria', 'LIS', 'art. 124', 'https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'DECLARACION_INFORMATIVA', 'Modelo 196 - Retenciones cuentas bancarias y depositos', 'anual', 'enero', '196', 'LIRPF', 'art. 101', 'AEAT modelo 196', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('196'), 'Modelo especifico para rendimientos de cuentas y depositos de entidades de credito.', 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'DECLARACION_INFORMATIVA', 'Modelo 193 - Retenciones capital mobiliario', 'anual', 'enero', '193', 'LIRPF', 'art. 101', 'AEAT modelo 193', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('193'), NULL, 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'DECLARACION_INFORMATIVA', 'Modelo 198 - Operaciones con activos financieros y valores', 'anual', 'enero-febrero', '198', NULL, NULL, 'AEAT modelo 198', 'norma_primaria', false, 'parcial', pg_temp.source_url_for_model('198'), 'Aplicabilidad condicionada a operaciones informables.', 'norma_primaria', 'AEAT_198', NULL, pg_temp.source_url_for_model('198'), 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'DECLARACION_INFORMATIVA', 'Modelo 289 - CRS cuentas financieras', 'anual', 'enero', '289', 'LGT', NULL, 'AEAT modelo 289', 'norma_primaria', false, 'parcial', pg_temp.source_url_for_model('289'), 'Institucion financiera obligada CRS cuando concurren condiciones reglamentarias.', 'norma_primaria', 'AEAT_289', NULL, pg_temp.source_url_for_model('289'), 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'DECLARACION_INFORMATIVA', 'Modelo 290 - FATCA cuentas financieras', 'anual', 'enero', '290', NULL, NULL, 'AEAT modelo 290', 'norma_primaria', false, 'parcial', pg_temp.source_url_for_model('290'), 'FATCA para cuentas financieras reportables.', 'norma_primaria', 'AEAT_290', NULL, pg_temp.source_url_for_model('290'), 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'DECLARACION_INFORMATIVA', 'Modelo 296 - IRNR retenciones resumen anual', 'anual', NULL, '296', 'TRLIRNR', 'art. 31', 'AEAT modelo 296', 'norma_primaria', true, 'parcial', pg_temp.source_url_for_model('296'), 'Solo si satisface rentas sujetas a retencion a no residentes.', 'norma_primaria', 'TRLIRNR', 'art. 31', 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-4527', 1);
END
$$;

-- Entidad de credito PBC/FT: base rows plus reinforced duties.
INSERT INTO obligacion_perfil (
    perfil_codigo, obligacion_tipo, descripcion, periodicidad, plazo_descripcion,
    modelo_aeat, norma_codigo, articulo_referencia, fuente_secundaria,
    evidencia_tipo, safe_to_answer, verified, completeness, source_url,
    capture_date, notas
)
SELECT
    'entidad_credito',
    obligacion_tipo,
    descripcion,
    periodicidad,
    plazo_descripcion,
    modelo_aeat,
    norma_codigo,
    articulo_referencia,
    fuente_secundaria,
    evidencia_tipo,
    safe_to_answer,
    verified,
    completeness,
    'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737',
    CURRENT_DATE,
    concat_ws(' ', notas, 'Perfil entidad_credito: sujeto obligado PBC/FT de alto riesgo por actividad financiera.')
FROM obligacion_perfil
WHERE perfil_codigo = 'sociedad_valores'
  AND norma_codigo = 'LEY10_2010'
ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion) DO UPDATE SET
    periodicidad = EXCLUDED.periodicidad,
    plazo_descripcion = EXCLUDED.plazo_descripcion,
    norma_codigo = EXCLUDED.norma_codigo,
    articulo_referencia = EXCLUDED.articulo_referencia,
    fuente_secundaria = EXCLUDED.fuente_secundaria,
    evidencia_tipo = EXCLUDED.evidencia_tipo,
    verified = EXCLUDED.verified,
    completeness = EXCLUDED.completeness,
    source_url = EXCLUDED.source_url,
    capture_date = EXCLUDED.capture_date,
    notas = EXCLUDED.notas;

DO $$
BEGIN
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'DILIGENCIA_DEBIDA', 'Diligencia reforzada en corresponsalia bancaria y banca privada', 'continua', 'Revision continua y aprobacion reforzada antes de iniciar o mantener la relacion', NULL, 'LEY10_2010', 'arts. 11-12; RD_304_2014 arts. 15-18', 'SEPBLAC obligaciones', 'norma_primaria', true, 'completa', 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 'Obligacion reforzada por perfil de alto riesgo de entidad de credito.', 'norma_primaria', 'LEY10_2010', 'arts. 11-12', 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'CONTROL_INTERNO', 'Examen externo anual PBC/FT por experto independiente', 'anual', 'Informe anual por experto externo', NULL, 'LEY10_2010', 'art. 28.1', 'SEPBLAC obligaciones', 'norma_primaria', true, 'completa', 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 'Obligatorio para entidades de credito salvo excepciones normativas concretas.', 'norma_primaria', 'LEY10_2010', 'art. 28.1', 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'REGISTRO', 'Declaracion de movimientos de efectivo S1/S2', 'ad_hoc', 'Por operacion cuando se superen umbrales legales de movimiento de efectivo', NULL, 'LEY10_2010', 'art. 34', 'SEPBLAC efectivo', 'norma_primaria', true, 'completa', 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 'Aplicable a operaciones de movimiento de medios de pago conforme a umbrales legales.', 'norma_primaria', 'LEY10_2010', 'art. 34', 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 1);
END
$$;

-- Entidad de credito prudential/BDE/DORA obligations.
DO $$
BEGIN
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'REPORTING', 'COREP - reporting prudencial recursos propios', 'trimestral', 'Reporting supervisorio trimestral', NULL, '32013R0575', 'art. 99', 'BDE/CRR COREP', 'reglamento_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0575', 'Reporting prudencial de recursos propios para entidades sujetas a CRR.', 'reglamento_ue', '32013R0575', 'art. 99', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0575', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'REPORTING', 'FINREP - reporting financiero supervisorio', 'trimestral', 'Reporting financiero trimestral y anual segun regimen supervisor', NULL, '32013R0575', 'art. 99', 'BDE/CRR FINREP', 'reglamento_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0575', 'Reporting financiero supervisorio bajo marco CRR/ITS.', 'reglamento_ue', '32013R0575', 'art. 99', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0575', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'REPORTING', 'Reporte ratio de liquidez LCR y NSFR', 'mensual', 'LCR mensual y NSFR segun calendario supervisor', NULL, '32013R0575', 'arts. 411-428', 'BDE/CRR liquidez', 'reglamento_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0575', 'Obligacion prudencial de liquidez para entidad de credito.', 'reglamento_ue', '32013R0575', 'arts. 411-428', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32013R0575', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'CONTROL_INTERNO', 'Marco de gestion del riesgo TIC DORA', 'continua', 'Obligacion permanente desde enero 2025', NULL, '32022R2554', 'arts. 5-16', 'DORA', 'reglamento_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 'Marco DORA aplicable a entidad financiera.', 'reglamento_ue', '32022R2554', 'arts. 5-16', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'CONTROL_INTERNO', 'Pruebas de resiliencia operativa digital DORA TLPT', 'anual', 'Periodicidad anual o trienal segun significatividad y designacion supervisora', NULL, '32022R2554', 'arts. 26-27', 'DORA TLPT', 'reglamento_ue', true, 'parcial', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 'TLPT aplica a entidades significativas o designadas; verificar alcance supervisor concreto.', 'reglamento_ue', '32022R2554', 'arts. 26-27', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 1);
    PERFORM pg_temp.seed_obligacion('entidad_credito', 'REPORTING', 'Reporting incidentes TIC graves DORA', 'ad_hoc', 'Cuando se produzca incidente TIC grave', NULL, '32022R2554', 'arts. 17-23', 'DORA incidentes', 'reglamento_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 'Notificacion de incidentes TIC graves bajo DORA.', 'reglamento_ue', '32022R2554', 'arts. 17-23', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 1);
END
$$;

-- Empresa de servicios de pago obligations.
DO $$
BEGIN
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'AUTOLIQUIDACION', 'Modelo 111 - Retenciones trabajo y actividades profesionales', 'trimestral', 'mensual o trimestral segun volumen y condiciones AEAT', '111', 'LIRPF', 'art. 101', 'AEAT modelo 111', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('111'), NULL, 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'AUTOLIQUIDACION', 'Modelo 115 - Retenciones por arrendamientos urbanos', 'trimestral', NULL, '115', 'LIRPF', 'art. 101', 'AEAT modelo 115', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('115'), NULL, 'norma_primaria', 'LIRPF', 'art. 101', 'https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'AUTOLIQUIDACION', 'Modelo 200 - Impuesto sobre Sociedades declaracion anual', 'anual', '25 dias naturales siguientes a los 6 meses posteriores al cierre', '200', 'LIS', 'art. 124', 'AEAT modelo 200', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('200'), NULL, 'norma_primaria', 'LIS', 'art. 124', 'https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'AUTOLIQUIDACION', 'Modelo 303 - IVA autoliquidacion', 'trimestral', 'trimestral salvo gran empresa u otros supuestos AEAT', '303', 'LIVA', 'art. 164', 'AEAT modelo 303', 'norma_primaria', true, 'completa', pg_temp.source_url_for_model('303'), 'Servicios de pago tratados como sujetos a IVA para este perfil operativo; verificar exenciones especificas si la actividad cambia.', 'norma_primaria', 'LIVA', 'art. 164', 'https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'REPORTING', 'Reporting operacional a BDE', 'anual', 'Informe operativo anual a supervisor', NULL, 'RD19_2018', 'art. 29', 'Banco de Espana PSD2', 'norma_primaria', true, 'completa', 'https://www.boe.es/buscar/act.php?id=BOE-A-2018-16036', 'Obligacion operativa de entidad de pago supervisada por BDE.', 'norma_primaria', 'RD19_2018', 'art. 29', 'https://www.boe.es/buscar/act.php?id=BOE-A-2018-16036', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'REPORTING', 'Reporte incidentes operativos y de seguridad a BDE', 'ad_hoc', 'Cuando se produzca incidente operativo o de seguridad grave', NULL, '32015L2366', 'art. 96', 'PSD2 incidentes', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015L2366', 'Notificacion de incidentes operativos y de seguridad bajo PSD2.', 'directiva_ue', '32015L2366', 'art. 96', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015L2366', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'CONTROL_INTERNO', 'Marco de seguridad de la informacion PSD2', 'anual', 'Revision e informe anual de seguridad', NULL, '32015L2366', 'art. 95', 'PSD2 seguridad', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015L2366', 'Marco de gestion de riesgos operativos y de seguridad.', 'directiva_ue', '32015L2366', 'art. 95', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015L2366', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'CONTROL_INTERNO', 'Autenticacion reforzada de clientes SCA', 'continua', 'Aplicacion continua en operaciones sujetas a SCA', NULL, '32015L2366', 'art. 97', 'PSD2 SCA', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015L2366', 'SCA bajo PSD2; RTS SCA pendiente de carga granular.', 'directiva_ue', '32015L2366', 'art. 97', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015L2366', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'DILIGENCIA_DEBIDA', 'PBC/FT si supera umbral de volumen de operaciones', 'continua', 'Condicionada a superar umbral y actividad sujeta', NULL, 'LEY10_2010', 'art. 2.1', 'SEPBLAC obligaciones', 'norma_primaria', false, 'parcial', 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 'Sujeto obligado PBC/FT si el perfil concreto supera umbral o realiza actividad sujeta; validar volumen.', 'norma_primaria', 'LEY10_2010', 'art. 2.1', 'https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737', 1);
    PERFORM pg_temp.seed_obligacion('empresa_servicios_pago', 'CONTROL_INTERNO', 'Marco de gestion del riesgo TIC DORA', 'continua', 'Obligacion permanente cuando clasifica como entidad financiera DORA', NULL, '32022R2554', 'arts. 5-16', 'DORA', 'reglamento_ue', true, 'parcial', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 'Aplicabilidad DORA condicionada a clasificacion como entidad financiera incluida.', 'reglamento_ue', '32022R2554', 'arts. 5-16', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 1);
END
$$;

-- Complete SGIIC with additional AIFMD/UCITS/ESMA/DORA obligations.
DO $$
BEGIN
    PERFORM pg_temp.seed_obligacion('sgiic', 'REPORTING', 'Reporte AIFMD Annex IV a CNMV', 'trimestral', 'Trimestral o semestral segun AUM y tipo de fondo', NULL, '32011L0061', 'Annex IV', 'AIFMD Annex IV', 'directiva_ue', false, 'parcial', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32011L0061', 'Periodicidad condicionada a umbrales AUM y tipo de vehiculo.', 'directiva_ue', '32011L0061', 'Annex IV', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32011L0061', 1);
    PERFORM pg_temp.seed_obligacion('sgiic', 'REPORTING', 'Reporte UCITS a CNMV', 'semestral', 'Informacion semestral y anual', NULL, '32009L0065', 'art. 83', 'UCITS reporting', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32009L0065', 'Reporting UCITS para gestoras y vehiculos aplicables.', 'directiva_ue', '32009L0065', 'art. 83', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32009L0065', 1);
    PERFORM pg_temp.seed_obligacion('sgiic', 'CONTROL_INTERNO', 'Politica de gestion de liquidez AIFMD art. 16', 'continua', 'Revision anual y seguimiento continuo', NULL, '32011L0061', 'art. 16', 'ESMA34-39-897', 'directiva_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32011L0061', 'Politica de liquidez y pruebas de stress vinculadas a AIFMD.', 'directiva_ue', '32011L0061', 'art. 16', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32011L0061', 1);
    PERFORM pg_temp.seed_obligacion('sgiic', 'CONTROL_INTERNO', 'Prueba de estres de liquidez', 'semestral', 'Semestral minimo segun guias ESMA y perfil del fondo', NULL, '32011L0061', 'art. 16', 'ESMA34-671404336-1364', 'directiva_ue', true, 'parcial', 'https://www.esma.europa.eu/sites/default/files/2026-03/ESMA34-671404336-1364_Guidelines_on_liquidity_management_tools_of_UCITS_and_AIFs.pdf', 'Guia ESMA 2026: aplicar segun tipo de IIC/AIF y calendario supervisor.', 'guideline_esma', 'ESMA34-671404336-1364', NULL, 'https://www.esma.europa.eu/sites/default/files/2026-03/ESMA34-671404336-1364_Guidelines_on_liquidity_management_tools_of_UCITS_and_AIFs.pdf', 2);
    PERFORM pg_temp.seed_obligacion('sgiic', 'REPORTING', 'Reporting herramientas gestion liquidez a CNMV', 'ad_hoc', 'Ad hoc y anual cuando CNMV/ESMA lo requiera', NULL, '32011L0061', 'art. 16', 'ESMA34-671404336-1364', 'guideline_esma', false, 'parcial', 'https://www.esma.europa.eu/sites/default/files/2026-03/ESMA34-671404336-1364_Guidelines_on_liquidity_management_tools_of_UCITS_and_AIFs.pdf', 'Nueva capa de reporting ligada a herramientas de gestion de liquidez; pendiente calendario nacional concreto.', 'guideline_esma', 'ESMA34-671404336-1364', NULL, 'https://www.esma.europa.eu/sites/default/files/2026-03/ESMA34-671404336-1364_Guidelines_on_liquidity_management_tools_of_UCITS_and_AIFs.pdf', 2);
    PERFORM pg_temp.seed_obligacion('sgiic', 'CONTROL_INTERNO', 'Marco de gestion del riesgo TIC DORA', 'continua', 'Obligacion permanente desde enero 2025', NULL, '32022R2554', 'arts. 5-16', 'DORA', 'reglamento_ue', true, 'completa', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 'DORA aplicable a SGIIC como entidad financiera.', 'reglamento_ue', '32022R2554', 'arts. 5-16', 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554', 1);
END
$$;

-- Agencia de valores: mark rows verifiable after Sprint D EU norm normalization where article is explicit.
UPDATE obligacion_perfil
SET verified = true,
    completeness = CASE WHEN completeness = 'parcial' THEN 'completa' ELSE completeness END,
    capture_date = CURRENT_DATE,
    notas = concat_ws(' ', notas, 'Sprint E: verificacion reforzada tras carga de normas UE Sprint D; mantener caveat de no custodia segun LIVMC art. 144.')
WHERE perfil_codigo = 'agencia_valores'
  AND norma_codigo IN ('32014R0600', '32013R0575', '32014L0065')
  AND articulo_referencia IS NOT NULL
  AND articulo_referencia <> '';

-- Secondary traceability to AEAT model pages for fiscal obligations.
DELETE FROM obligacion_fuente fuente
USING obligacion_perfil obligacion
WHERE fuente.obligacion_id = obligacion.id
  AND fuente.fuente_tipo = 'modelo_aeat'
  AND obligacion.perfil_codigo IN ('eaf', 'entidad_credito', 'empresa_servicios_pago');

INSERT INTO obligacion_fuente (
    obligacion_id,
    fuente_tipo,
    codigo_referencia,
    articulo,
    descripcion,
    source_url,
    peso
)
SELECT
    obligacion.id,
    'modelo_aeat',
    'Modelo ' || obligacion.modelo_aeat,
    NULL,
    obligacion.descripcion,
    obligacion.source_url,
    2
FROM obligacion_perfil obligacion
WHERE obligacion.perfil_codigo IN ('eaf', 'entidad_credito', 'empresa_servicios_pago')
  AND obligacion.modelo_aeat IS NOT NULL
  AND obligacion.source_url IS NOT NULL
  AND obligacion.source_url <> '';

COMMIT;
