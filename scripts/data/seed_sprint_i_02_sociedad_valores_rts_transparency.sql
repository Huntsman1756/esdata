BEGIN;

INSERT INTO norma (
    codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
    tipo_documento, ambito, estado_cobertura, vigente_desde,
    celex, tipo_norma, publicacion_doue, url_eurlex, vigente
) VALUES (
    '32014R0600',
    'Reglamento (UE) n. 600/2014 relativo a los mercados de instrumentos financieros (MiFIR)',
    'EUR-CELEX-32014R0600',
    'http://data.europa.eu/eli/reg/2014/600/oj',
    'ue',
    'eurlex',
    'reglamento_ue',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2014-06-12',
    '32014R0600',
    'reglamento_ue',
    DATE '2014-06-12',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600',
    TRUE
)
ON CONFLICT (codigo) DO UPDATE SET
    titulo = EXCLUDED.titulo,
    boe_id = EXCLUDED.boe_id,
    eli_uri = EXCLUDED.eli_uri,
    jurisdiccion = EXCLUDED.jurisdiccion,
    tipo_fuente = EXCLUDED.tipo_fuente,
    tipo_documento = EXCLUDED.tipo_documento,
    ambito = EXCLUDED.ambito,
    estado_cobertura = EXCLUDED.estado_cobertura,
    vigente_desde = EXCLUDED.vigente_desde,
    celex = EXCLUDED.celex,
    tipo_norma = EXCLUDED.tipo_norma,
    publicacion_doue = EXCLUDED.publicacion_doue,
    url_eurlex = EXCLUDED.url_eurlex,
    vigente = EXCLUDED.vigente;

DO $$
DECLARE
    missing_norms TEXT;
BEGIN
    SELECT string_agg(codigo, ', ' ORDER BY codigo)
    INTO missing_norms
    FROM (
        VALUES ('32014R0600'), ('32017R0587'), ('32017R0583')
    ) AS required(codigo)
    WHERE NOT EXISTS (SELECT 1 FROM norma n WHERE n.codigo = required.codigo);

    IF missing_norms IS NOT NULL THEN
        RAISE EXCEPTION 'Missing required norma rows: %', missing_norms;
    END IF;
END
$$;

INSERT INTO perfil_entidad (
    codigo, nombre, descripcion, supervisor, regimen_primario, activo, notas
) VALUES (
    'sociedad_valores',
    'Sociedad de Valores',
    'Empresa de servicios de inversion que puede quedar sujeta a transparencia MiFIR si opera como internalizador sistematico u operador de centro de negociacion.',
    'CNMV',
    'LIVMC/MiFIR',
    TRUE,
    'Sprint I: perfil minimo para obligaciones MiFIR RTS 1/2 condicionadas a estatus SI.'
)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    supervisor = EXCLUDED.supervisor,
    regimen_primario = EXCLUDED.regimen_primario,
    activo = EXCLUDED.activo,
    notas = EXCLUDED.notas;

CREATE OR REPLACE FUNCTION pg_temp.seed_obligacion_i02(
    p_tipo TEXT,
    p_descripcion TEXT,
    p_periodicidad TEXT,
    p_norma TEXT,
    p_articulo TEXT,
    p_source_url TEXT,
    p_notas TEXT
) RETURNS INTEGER AS $$
DECLARE
    row_id INTEGER;
BEGIN
    INSERT INTO obligacion_perfil (
        perfil_codigo,
        obligacion_tipo,
        descripcion,
        periodicidad,
        norma_codigo,
        articulo_referencia,
        evidencia_tipo,
        safe_to_answer,
        verified,
        completeness,
        source_url,
        capture_date,
        notas
    ) VALUES (
        'sociedad_valores',
        p_tipo,
        p_descripcion,
        p_periodicidad,
        p_norma,
        p_articulo,
        'norma_primaria',
        TRUE,
        TRUE,
        'parcial',
        p_source_url,
        CURRENT_DATE,
        p_notas
    )
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion) DO UPDATE SET
        periodicidad = EXCLUDED.periodicidad,
        norma_codigo = EXCLUDED.norma_codigo,
        articulo_referencia = EXCLUDED.articulo_referencia,
        evidencia_tipo = EXCLUDED.evidencia_tipo,
        safe_to_answer = EXCLUDED.safe_to_answer,
        verified = EXCLUDED.verified,
        completeness = EXCLUDED.completeness,
        source_url = EXCLUDED.source_url,
        capture_date = EXCLUDED.capture_date,
        notas = EXCLUDED.notas
    RETURNING id INTO row_id;

    DELETE FROM obligacion_fuente
    WHERE obligacion_id = row_id
      AND fuente_tipo IN ('reglamento_ue', 'reglamento_delegado_ue');

    INSERT INTO obligacion_fuente (
        obligacion_id, fuente_tipo, codigo_referencia, articulo,
        descripcion, source_url, peso
    ) VALUES (
        row_id,
        CASE WHEN p_norma = '32014R0600' THEN 'reglamento_ue' ELSE 'reglamento_delegado_ue' END,
        p_norma,
        p_articulo,
        p_descripcion,
        p_source_url,
        1
    );

    RETURN row_id;
END;
$$ LANGUAGE plpgsql;

SELECT pg_temp.seed_obligacion_i02(
    'REPORTING',
    'Publicacion de cotizaciones pre-negociacion (SI renta variable)',
    'continua',
    '32017R0587',
    'art. 8',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0587',
    'Solo si registrada como Internalizador Sistematico (SI) para instrumentos de renta variable ante CNMV/ESMA. RTS 1 art. 8: publicacion de cotizaciones firmes. Exenciones LIS en art. 9.'
);

SELECT pg_temp.seed_obligacion_i02(
    'REPORTING',
    'Publicacion de cotizaciones pre-negociacion (SI no renta variable)',
    'continua',
    '32017R0583',
    'art. 8',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0583',
    'Solo si registrada como SI para instrumentos de deuda, derivados, productos estructurados o derechos de emision.'
);

SELECT pg_temp.seed_obligacion_i02(
    'REPORTING',
    'Publicacion post-negociacion de operaciones (RTS 1)',
    'continua',
    '32017R0587',
    'art. 6',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0587',
    'Publicacion tan cercana al tiempo real como sea posible. Distinto de transaction reporting (RTS 22). Aplica si ejecuta operaciones en instrumentos de renta variable fuera de mercado. Exenciones por tamano (LIS) en art. 7.'
);

SELECT pg_temp.seed_obligacion_i02(
    'REPORTING',
    'Publicacion post-negociacion de operaciones (RTS 2)',
    'continua',
    '32017R0583',
    'art. 10',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0583',
    'Publicacion post-negociacion para instrumentos no renta variable. Aplica si ejecuta operaciones fuera de mercado. Exenciones en art. 11.'
);

SELECT pg_temp.seed_obligacion_i02(
    'CONTROL_INTERNO',
    'Politica de internalizador sistematico (SI)',
    'anual',
    '32014R0600',
    'art. 13',
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600',
    'Si la entidad supera los umbrales de SI definidos en MiFIR art. 4, debe notificar a CNMV y cumplir obligaciones SI. Umbrales calculados semestralmente. RTS 1 art. 12-17 para equity.'
);

COMMIT;
