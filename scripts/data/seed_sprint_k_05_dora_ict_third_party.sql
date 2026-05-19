-- Sprint K K-05: DORA ICT third-party contractual arrangements.
--
-- Applies to DORA in-scope profiles. EAF rows remain partial because
-- DORA art. 2.3 exempts microenterprises.

WITH profiles AS (
    SELECT *
    FROM (VALUES
        ('sociedad_valores'::varchar, 'completa'::varchar, ''::text),
        ('agencia_valores', 'completa', ''),
        ('entidad_credito', 'completa', ''),
        ('sgiic', 'completa', ''),
        ('empresa_servicios_pago', 'completa', ''),
        ('eaf', 'parcial', ' Condicional para EAF: solo si supera umbral microempresa DORA art. 2.3.')
    ) AS p(perfil_codigo, completeness, extra_note)
),
obligations AS (
    SELECT *
    FROM (VALUES
        (
            'CONTROL_INTERNO'::varchar,
            'Registro de informacion de terceros TIC (DORA art. 28)'::text,
            'continua'::varchar,
            'art. 28'::text,
            'DORA art. 28: registro completo de todos los acuerdos contractuales con proveedores terceros de servicios TIC. RTS 32024R1773 define el contenido minimo del registro. Obligatorio desde 17 enero 2025.'::text
        ),
        (
            'CONTROL_INTERNO',
            'Clausulas contractuales minimas proveedores TIC',
            'continua',
            'art. 30',
            'DORA art. 30: todo contrato con proveedor TIC debe incluir clausulas minimas: descripcion servicios, niveles de servicio, plan de continuidad, derecho de auditoria, terminacion. RTS 32024R1773 desarrolla la politica contractual.'
        )
    ) AS o(obligacion_tipo, descripcion, periodicidad, articulo_referencia, base_note)
),
rows AS (
    SELECT
        p.perfil_codigo,
        o.obligacion_tipo,
        o.descripcion,
        o.periodicidad,
        '32022R2554'::varchar AS norma_codigo,
        o.articulo_referencia,
        '32024R1773 (RTS acuerdos contractuales TIC)'::text AS fuente_secundaria,
        'official_exact'::varchar AS evidencia_tipo,
        TRUE AS safe_to_answer,
        TRUE AS verified,
        p.completeness,
        'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554'::text AS source_url,
        o.base_note || p.extra_note AS notas
    FROM profiles p
    CROSS JOIN obligations o
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
),
sources AS (
    SELECT
        id AS obligacion_id,
        'norma_eu'::varchar AS fuente_tipo,
        norma_codigo AS codigo_referencia,
        articulo_referencia AS articulo,
        'DORA base verificada en EUR-Lex para ' || descripcion AS descripcion,
        source_url,
        1 AS peso
    FROM upserted
    UNION ALL
    SELECT
        id AS obligacion_id,
        'norma_eu'::varchar AS fuente_tipo,
        '32024R1773'::text AS codigo_referencia,
        articulo_referencia AS articulo,
        'RTS DORA sobre acuerdos contractuales con terceros TIC verificado en EUR-Lex',
        'https://eur-lex.europa.eu/legal-content/ES/ALL/?uri=CELEX:32024R1773',
        2 AS peso
    FROM upserted
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
    s.obligacion_id,
    s.fuente_tipo,
    s.codigo_referencia,
    s.articulo,
    s.descripcion,
    s.source_url,
    s.peso
FROM sources s
WHERE NOT EXISTS (
    SELECT 1
    FROM obligacion_fuente f
    WHERE f.obligacion_id = s.obligacion_id
      AND f.codigo_referencia = s.codigo_referencia
      AND f.articulo = s.articulo
      AND f.source_url = s.source_url
);
