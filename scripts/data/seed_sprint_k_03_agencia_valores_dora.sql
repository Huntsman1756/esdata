-- Sprint K K-03: DORA obligations for agencia_valores.
--
-- DORA art. 2.1.a includes investment firms in scope.
-- agencia_valores is an ESI profile supervised by CNMV.

WITH rows AS (
    SELECT *
    FROM (VALUES
        (
            'agencia_valores'::varchar,
            'CONTROL_INTERNO'::varchar,
            'Marco de gestion del riesgo TIC (DORA)'::text,
            'continua'::varchar,
            '32022R2554'::varchar,
            'art. 5'::text,
            '32024R1774 (RTS ICT risk management)'::text,
            'official_exact'::varchar,
            TRUE,
            TRUE,
            'completa'::varchar,
            'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554'::text,
            'DORA art. 5: marco de gobernanza y control del riesgo TIC. Aplicable desde 17 enero 2025. RTS detallado en 32024R1774. agencia_valores: aplica como ESI bajo DORA art. 2.1.a.'::text
        ),
        (
            'agencia_valores',
            'REPORTING',
            'Reporting incidentes TIC graves a CNMV/ESMA (DORA)',
            'ad_hoc',
            '32022R2554',
            'art. 19',
            'DORA incident reporting',
            'official_exact',
            TRUE,
            TRUE,
            'completa',
            'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554',
            'DORA art. 19: notificacion de incidentes TIC graves al supervisor competente (CNMV para ESI). Informe inicial, intermedio y final. Aplicable desde 17 enero 2025.'
        ),
        (
            'agencia_valores',
            'CONTROL_INTERNO',
            'Pruebas de resiliencia operativa digital (DORA)',
            'anual',
            '32022R2554',
            'art. 24',
            'DORA digital operational resilience testing',
            'official_exact',
            TRUE,
            TRUE,
            'completa',
            'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554',
            'DORA art. 24: pruebas basicas de resiliencia TIC (vulnerability assessments, network security tests). TLPT (arts. 26-27) solo para entidades significativas designadas por supervisor. agencia_valores: pruebas basicas, no TLPT salvo designacion.'
        )
    ) AS v (
        perfil_codigo,
        obligacion_tipo,
        descripcion,
        periodicidad,
        norma_codigo,
        articulo_referencia,
        fuente_secundaria,
        evidencia_tipo,
        safe_to_answer,
        verified,
        completeness,
        source_url,
        notas
    )
),
upserted AS (
    INSERT INTO obligacion_perfil (
        perfil_codigo,
        obligacion_tipo,
        descripcion,
        periodicidad,
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
    )
    SELECT
        perfil_codigo,
        obligacion_tipo,
        descripcion,
        periodicidad,
        norma_codigo,
        articulo_referencia,
        fuente_secundaria,
        evidencia_tipo,
        safe_to_answer,
        verified,
        completeness,
        source_url,
        CURRENT_DATE,
        notas
    FROM rows
    ON CONFLICT (perfil_codigo, obligacion_tipo, descripcion) DO UPDATE
    SET periodicidad = EXCLUDED.periodicidad,
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
    RETURNING id, norma_codigo, articulo_referencia, descripcion, source_url
)
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
    u.id,
    'norma_eu',
    u.norma_codigo,
    u.articulo_referencia,
    'DORA base verificada en EUR-Lex para ' || u.descripcion,
    u.source_url,
    1
FROM upserted u
WHERE NOT EXISTS (
    SELECT 1
    FROM obligacion_fuente f
    WHERE f.obligacion_id = u.id
      AND f.codigo_referencia = u.norma_codigo
      AND f.articulo = u.articulo_referencia
      AND f.source_url = u.source_url
);
