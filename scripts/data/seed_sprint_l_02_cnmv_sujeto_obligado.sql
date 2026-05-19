-- Sprint L L-02: map CNMV documents to applicable entity profiles.
--
-- The canonical query column is documento_interpretativo.sujeto_obligado text[].
-- We also mirror the value in metadata->'sujeto_obligado' for compatibility
-- with older metadata-based diagnostics.

WITH scoped AS (
    SELECT
        id,
        tipo_documento,
        numero_circular,
        lower(
            concat_ws(
                ' ',
                COALESCE(titulo, ''),
                COALESCE(ambito_tematico, ''),
                COALESCE(texto, '')
            )
        ) AS searchable
    FROM documento_interpretativo
    WHERE organismo_emisor = 'CNMV'
      AND tipo_fuente = 'cnmv'
),
mapped AS (
    SELECT
        id,
        ARRAY(
            SELECT DISTINCT value
            FROM unnest(
                ARRAY['sociedad_valores', 'agencia_valores']::text[]
                ||
                CASE
                    WHEN tipo_documento = 'documento_consulta_cnmv'
                      OR numero_circular IN ('1/2013', '4/2008', '1/2010', '3/2013')
                      OR searchable LIKE '%sgiic%'
                      OR searchable LIKE '%gestora%'
                      OR searchable LIKE '%gestoras%'
                      OR searchable LIKE '%iic%'
                      OR searchable LIKE '%instituciones de inversion colectiva%'
                      OR searchable LIKE '%instituciones de inversión colectiva%'
                      OR searchable LIKE '%ucits%'
                    THEN ARRAY['sgiic']::text[]
                    ELSE ARRAY[]::text[]
                END
                ||
                CASE
                    WHEN searchable LIKE '%entidad de credito%'
                      OR searchable LIKE '%entidad de crédito%'
                      OR searchable LIKE '%entidades de credito%'
                      OR searchable LIKE '%entidades de crédito%'
                    THEN ARRAY['entidad_credito']::text[]
                    ELSE ARRAY[]::text[]
                END
            ) AS value
            ORDER BY value
        ) AS perfiles
    FROM scoped
)
UPDATE documento_interpretativo d
SET sujeto_obligado = mapped.perfiles,
    metadata = jsonb_set(
        COALESCE(d.metadata, '{}'::jsonb),
        '{sujeto_obligado}',
        to_jsonb(mapped.perfiles),
        true
    )
FROM mapped
WHERE d.id = mapped.id;
