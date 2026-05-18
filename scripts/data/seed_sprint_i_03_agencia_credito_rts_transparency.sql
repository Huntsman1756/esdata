BEGIN;

DO $$
DECLARE
    missing_norms TEXT;
BEGIN
    SELECT string_agg(codigo, ', ' ORDER BY codigo)
    INTO missing_norms
    FROM (
        VALUES ('32017R0587'), ('32017R0583')
    ) AS required(codigo)
    WHERE NOT EXISTS (SELECT 1 FROM norma n WHERE n.codigo = required.codigo);

    IF missing_norms IS NOT NULL THEN
        RAISE EXCEPTION 'Missing required norma rows: %', missing_norms;
    END IF;
END
$$;

INSERT INTO perfil_entidad (
    codigo, nombre, descripcion, supervisor, regimen_primario, activo, notas
) VALUES
(
    'agencia_valores',
    'Agencia de Valores',
    'Empresa de servicios de inversion que puede quedar sujeta a transparencia MiFIR si opera como internalizador sistematico.',
    'CNMV',
    'LIVMC/MiFIR',
    TRUE,
    'Sprint I: SI menos probable por limitaciones operativas, pero juridicamente posible si registra actividad SI.'
),
(
    'entidad_credito',
    'Entidad de Credito',
    'Entidad de credito sujeta a MiFIR cuando presta servicios o actividades de inversion sobre instrumentos financieros.',
    'BDE',
    'CRR/MiFIR',
    TRUE,
    'Sprint I: MiFIR aplica cuando presta servicios de inversion; obligaciones RTS 1/2 solo si registra estatus SI.'
)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    supervisor = EXCLUDED.supervisor,
    regimen_primario = EXCLUDED.regimen_primario,
    activo = EXCLUDED.activo,
    notas = EXCLUDED.notas;

CREATE OR REPLACE FUNCTION pg_temp.seed_rts_transparency_i03(
    p_perfil TEXT,
    p_descripcion_suffix TEXT
) RETURNS VOID AS $$
DECLARE
    credit_note TEXT := CASE
        WHEN p_perfil = 'entidad_credito'
        THEN ' Aplica cuando la entidad de credito presta servicios de inversion en instrumentos financieros (MiFIR art. 1.2).'
        ELSE ''
    END;
    row_id INTEGER;
    obligation RECORD;
BEGIN
    FOR obligation IN
        SELECT *
        FROM (
            VALUES
            (
                'Publicacion de cotizaciones pre-negociacion (SI renta variable)',
                '32017R0587',
                'art. 8',
                'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0587',
                'Solo si registrada como Internalizador Sistematico (SI) para instrumentos de renta variable ante CNMV/ESMA. RTS 1 art. 8: publicacion de cotizaciones firmes. Exenciones LIS en art. 9.'
            ),
            (
                'Publicacion de cotizaciones pre-negociacion (SI no renta variable)',
                '32017R0583',
                'art. 8',
                'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0583',
                'Solo si registrada como SI para instrumentos de deuda, derivados, productos estructurados o derechos de emision.'
            ),
            (
                'Publicacion post-negociacion de operaciones (RTS 1)',
                '32017R0587',
                'art. 6',
                'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0587',
                'Publicacion tan cercana al tiempo real como sea posible. Distinto de transaction reporting (RTS 22). Aplica si ejecuta operaciones en instrumentos de renta variable fuera de mercado. Exenciones por tamano (LIS) en art. 7.'
            ),
            (
                'Publicacion post-negociacion de operaciones (RTS 2)',
                '32017R0583',
                'art. 10',
                'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0583',
                'Publicacion post-negociacion para instrumentos no renta variable. Aplica si ejecuta operaciones fuera de mercado. Exenciones en art. 11.'
            )
        ) AS rows(descripcion, norma_codigo, articulo, source_url, notas)
    LOOP
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
            p_perfil,
            'REPORTING',
            obligation.descripcion,
            'continua',
            obligation.norma_codigo,
            obligation.articulo,
            'norma_primaria',
            TRUE,
            TRUE,
            'parcial',
            obligation.source_url,
            CURRENT_DATE,
            obligation.notas || p_descripcion_suffix || credit_note
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
          AND fuente_tipo = 'reglamento_delegado_ue';

        INSERT INTO obligacion_fuente (
            obligacion_id, fuente_tipo, codigo_referencia, articulo,
            descripcion, source_url, peso
        ) VALUES (
            row_id,
            'reglamento_delegado_ue',
            obligation.norma_codigo,
            obligation.articulo,
            obligation.descripcion,
            obligation.source_url,
            1
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

SELECT pg_temp.seed_rts_transparency_i03(
    'agencia_valores',
    ' Agencia de valores: condicionada a estatus SI; menos frecuente por ausencia de negociacion por cuenta propia, pero no se carga como universal.'
);

SELECT pg_temp.seed_rts_transparency_i03(
    'entidad_credito',
    ' Entidad de credito: condicionada a estatus SI y a prestar servicios de inversion.'
);

COMMIT;
