-- Sprint K K-04: conditional DORA obligations for EAF.
--
-- EAF is treated as an ESI profile, but DORA art. 2.3 exempts
-- microenterprises. Therefore DORA obligations are verified but partial.

WITH rows AS (
    SELECT *
    FROM (VALUES
        (
            'eaf'::varchar,
            'CONTROL_INTERNO'::varchar,
            'Marco de gestion del riesgo TIC (DORA)'::text,
            'continua'::varchar,
            '32022R2554'::varchar,
            'art. 5'::text,
            '32024R1774 (RTS simplified ICT risk management framework)'::text,
            'official_exact'::varchar,
            TRUE,
            TRUE,
            'parcial'::varchar,
            'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554'::text,
            'DORA art. 2.1.a: EAF como ESI esta en ambito DORA. CONDICION: si la EAF supera umbral microempresa (art. 2.3: >= 10 empleados O >= 2M EUR facturacion/balance), aplica el marco TIC. Si es microempresa: exenta de DORA. La mayoria de EAF en Espana son microempresas. RTS simplificado en 32024R1774.'::text
        ),
        (
            'eaf',
            'REPORTING',
            'Reporting incidentes TIC graves (DORA)',
            'ad_hoc',
            '32022R2554',
            'art. 19',
            'DORA incident reporting',
            'official_exact',
            TRUE,
            TRUE,
            'parcial',
            'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554',
            'Condicional: solo si EAF supera umbral microempresa DORA art. 2.3. Ver obligacion Marco TIC para condicion completa. Si aplica, DORA art. 19 exige notificacion de incidentes TIC graves al supervisor competente.'
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
