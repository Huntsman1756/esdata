-- ESData production integrity check.
-- Run from the repository root:
--   cat scripts/integrity-check.sql | docker compose --env-file /etc/esdata/esdata.env \
--     -f infra/deploy/docker-compose.prod.yml exec -T postgres \
--     psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -

\set ON_ERROR_STOP on
\pset pager off

CREATE TEMP TABLE integrity_failures (
    check_group text NOT NULL,
    check_name text NOT NULL,
    failing_rows bigint NOT NULL
);

CREATE TEMP TABLE integrity_warnings (
    check_group text NOT NULL,
    check_name text NOT NULL,
    affected_rows bigint NOT NULL,
    note text NOT NULL
);

-- Foreign-key constraints must be validated by PostgreSQL.
INSERT INTO integrity_failures (check_group, check_name, failing_rows)
SELECT
    'foreign_key',
    conrelid::regclass::text || '.' || conname || ' is not validated',
    1
FROM pg_constraint
WHERE contype = 'f'
  AND NOT convalidated;

-- Defensive orphan scans on compliance-critical relationships.
INSERT INTO integrity_failures
SELECT 'foreign_key', 'articulo.norma_id -> norma.id', count(*)
FROM articulo a
LEFT JOIN norma n ON n.id = a.norma_id
WHERE n.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'version_articulo.articulo_id -> articulo.id', count(*)
FROM version_articulo va
LEFT JOIN articulo a ON a.id = va.articulo_id
WHERE a.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'articulo_materia.articulo_id -> articulo.id', count(*)
FROM articulo_materia am
LEFT JOIN articulo a ON a.id = am.articulo_id
WHERE a.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'articulo_materia.materia_id -> materia.id', count(*)
FROM articulo_materia am
LEFT JOIN materia m ON m.id = am.materia_id
WHERE m.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'modelo_articulo.modelo_id -> aeat_modelo.id', count(*)
FROM modelo_articulo ma
LEFT JOIN aeat_modelo m ON m.id = ma.modelo_id
WHERE m.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'modelo_articulo.articulo_id -> articulo.id', count(*)
FROM modelo_articulo ma
LEFT JOIN articulo a ON a.id = ma.articulo_id
WHERE a.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'modelo_campana.modelo_id -> aeat_modelo.id', count(*)
FROM modelo_campana mc
LEFT JOIN aeat_modelo m ON m.id = mc.modelo_id
WHERE m.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'modelo_casilla.campana_id -> modelo_campana.id', count(*)
FROM modelo_casilla mc
LEFT JOIN modelo_campana mcp ON mcp.id = mc.campana_id
WHERE mcp.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'modelo_instruccion.campana_id -> modelo_campana.id', count(*)
FROM modelo_instruccion mi
LEFT JOIN modelo_campana mcp ON mcp.id = mi.campana_id
WHERE mcp.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'modelo_normativa.modelo_id -> aeat_modelo.id', count(*)
FROM modelo_normativa mn
LEFT JOIN aeat_modelo m ON m.id = mn.modelo_id
WHERE m.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'modelo_recurso.campana_id -> modelo_campana.id', count(*)
FROM modelo_recurso mr
LEFT JOIN modelo_campana mcp ON mcp.id = mr.campana_id
WHERE mcp.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'documento_articulo.documento_id -> documento_interpretativo.id', count(*)
FROM documento_articulo da
LEFT JOIN documento_interpretativo di ON di.id = da.documento_id
WHERE di.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'documento_articulo.articulo_id -> articulo.id', count(*)
FROM documento_articulo da
LEFT JOIN articulo a ON a.id = da.articulo_id
WHERE a.id IS NULL
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'foreign_key', 'documento_version.documento_referencia -> documento_interpretativo.referencia', count(*)
FROM documento_version dv
LEFT JOIN documento_interpretativo di ON di.referencia = dv.documento_referencia
WHERE di.referencia IS NULL
HAVING count(*) > 0;

-- Generic null scan over every NOT NULL column in the public schema.
DO $$
DECLARE
    r record;
    n bigint;
BEGIN
    FOR r IN
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND is_nullable = 'NO'
          AND table_name NOT LIKE 'pg_%'
    LOOP
        EXECUTE format(
            'SELECT count(*) FROM %I WHERE %I IS NULL',
            r.table_name,
            r.column_name
        ) INTO n;

        IF n > 0 THEN
            INSERT INTO integrity_failures
            VALUES ('not_null', r.table_name || '.' || r.column_name || ' is NULL', n);
        END IF;
    END LOOP;
END $$;

-- Empty-string checks for compliance-critical text columns.
INSERT INTO integrity_failures
SELECT 'content_required', 'norma.codigo is empty', count(*)
FROM norma
WHERE btrim(codigo) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'norma.titulo is empty', count(*)
FROM norma
WHERE btrim(titulo) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'norma.boe_id is empty', count(*)
FROM norma
WHERE btrim(boe_id) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'version_articulo.texto is empty', count(*)
FROM version_articulo
WHERE btrim(texto) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'aeat_modelo.codigo is empty', count(*)
FROM aeat_modelo
WHERE btrim(codigo) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'aeat_modelo.nombre is empty', count(*)
FROM aeat_modelo
WHERE btrim(nombre) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'modelo_campana.campana is empty', count(*)
FROM modelo_campana
WHERE btrim(campana) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'modelo_casilla.codigo is empty', count(*)
FROM modelo_casilla
WHERE btrim(codigo) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'modelo_casilla.etiqueta is empty', count(*)
FROM modelo_casilla
WHERE btrim(etiqueta) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'documento_interpretativo.referencia is empty', count(*)
FROM documento_interpretativo
WHERE btrim(referencia) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'documento_interpretativo.texto is empty for complete rows', count(*)
FROM documento_interpretativo
WHERE btrim(texto) = ''
  AND row_completeness = 'complete'
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'sync_log.worker is empty', count(*)
FROM sync_log
WHERE btrim(worker) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'query_audit_log.request_id is empty', count(*)
FROM query_audit_log
WHERE btrim(request_id) = ''
HAVING count(*) > 0;

INSERT INTO integrity_failures
SELECT 'content_required', 'query_audit_log.tool_name is empty', count(*)
FROM query_audit_log
WHERE btrim(tool_name) = ''
HAVING count(*) > 0;

-- Logical key duplication. Unique indexes should enforce these, but this
-- makes the audit output explicit and catches legacy drift if constraints move.
INSERT INTO integrity_failures
SELECT 'logical_key', 'articulo(norma_id, numero)', count(*) - count(DISTINCT (norma_id, numero))
FROM articulo
HAVING count(*) - count(DISTINCT (norma_id, numero)) > 0;

INSERT INTO integrity_failures
SELECT 'logical_key', 'aeat_modelo(codigo)', count(*) - count(DISTINCT codigo)
FROM aeat_modelo
HAVING count(*) - count(DISTINCT codigo) > 0;

INSERT INTO integrity_failures
SELECT 'logical_key', 'documento_interpretativo(referencia)', count(*) - count(DISTINCT referencia)
FROM documento_interpretativo
HAVING count(*) - count(DISTINCT referencia) > 0;

INSERT INTO integrity_failures
SELECT 'logical_key', 'modelo_articulo(modelo_id, articulo_id)', count(*) - count(DISTINCT (modelo_id, articulo_id))
FROM modelo_articulo
HAVING count(*) - count(DISTINCT (modelo_id, articulo_id)) > 0;

INSERT INTO integrity_failures
SELECT 'logical_key', 'modelo_articulo(modelo_id, norma, numero)', count(*) - count(DISTINCT (modelo_id, norma, numero))
FROM modelo_articulo
HAVING count(*) - count(DISTINCT (modelo_id, norma, numero)) > 0;

INSERT INTO integrity_failures
SELECT 'logical_key', 'modelo_campana(modelo_id, campana)', count(*) - count(DISTINCT (modelo_id, campana))
FROM modelo_campana
HAVING count(*) - count(DISTINCT (modelo_id, campana)) > 0;

INSERT INTO integrity_failures
SELECT 'logical_key', 'modelo_casilla(campana_id, codigo)', count(*) - count(DISTINCT (campana_id, codigo))
FROM modelo_casilla
HAVING count(*) - count(DISTINCT (campana_id, codigo)) > 0;

-- Non-blocking completeness warnings: these rows are explicitly partial and
-- must not be presented as complete authoritative text by retrieval tools.
INSERT INTO integrity_warnings
SELECT
    'partial_content',
    'documento_interpretativo.texto empty on partial rows',
    count(*),
    'Allowed only because row_completeness <> complete and url_fuente preserves the official source.'
FROM documento_interpretativo
WHERE btrim(texto) = ''
  AND row_completeness <> 'complete'
HAVING count(*) > 0;

INSERT INTO integrity_warnings
SELECT
    'optional_metadata',
    'aeat_modelo.periodo empty',
    count(*),
    'Non-blocking: periodo is nullable because not every AEAT model page exposes cadence.'
FROM aeat_modelo
WHERE periodo IS NULL OR btrim(periodo) = ''
HAVING count(*) > 0;

\echo 'Integrity warnings (non-blocking):'
TABLE integrity_warnings;

DO $$
DECLARE
    failure_count bigint;
BEGIN
    SELECT count(*) INTO failure_count FROM integrity_failures;
    IF failure_count > 0 THEN
        RAISE NOTICE 'Integrity failures:';
        PERFORM pg_catalog.pg_sleep(0);
        RAISE EXCEPTION 'integrity check failed: % blocking findings', failure_count;
    END IF;
END $$;

\echo 'PASS integrity checks'
