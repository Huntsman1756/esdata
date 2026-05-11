-- Integrity Check for esdata database
-- Run: docker compose exec postgres psql -U esdata -d esdata -f scripts/integrity-check.sql

\echo '=== 1. FK Violations ==='
SELECT 'ariculo_materia: articulo_id' AS fk_check, COUNT(*) AS violations
FROM articulo_materia am
LEFT JOIN articulo a ON a.id = am.articulo_id
WHERE a.id IS NULL
UNION ALL
SELECT 'ariculo_materia: materia_id', COUNT(*)
FROM articulo_materia am
LEFT JOIN materia m ON m.id = am.materia_id
WHERE m.id IS NULL
UNION ALL
SELECT 'modelo_articulo: modelo_id', COUNT(*)
FROM modelo_articulo ma
LEFT JOIN aeat_modelo m ON m.id = ma.modelo_id
WHERE m.id IS NULL
UNION ALL
SELECT 'modelo_articulo: articulo_id', COUNT(*)
FROM modelo_articulo ma
LEFT JOIN articulo a ON a.id = ma.articulo_id
WHERE a.id IS NULL
UNION ALL
SELECT 'modelo_campana: modelo_id', COUNT(*)
FROM modelo_campana mc
LEFT JOIN aeat_modelo m ON m.id = mc.modelo_id
WHERE m.id IS NULL
UNION ALL
SELECT 'documento_interpretativo: articulo_id', COUNT(*)
FROM documento_interpretativo di
LEFT JOIN articulo a ON a.id = di.articulo_id
WHERE di.articulo_id IS NOT NULL AND a.id IS NULL
UNION ALL
SELECT 'documento_articulo: documento_id', COUNT(*)
FROM documento_articulo da
LEFT JOIN documento_interpretativo di ON di.id = da.documento_id
WHERE di.id IS NULL
UNION ALL
SELECT 'version_articulo: articulo_id', COUNT(*)
FROM version_articulo va
LEFT JOIN articulo a ON a.id = va.articulo_id
WHERE a.id IS NULL
UNION ALL
SELECT 'modelo_casilla: modelo_campana_id', COUNT(*)
FROM modelo_casilla mc
LEFT JOIN modelo_campana mcp ON mcp.id = mc.modelo_campana_id
WHERE mcp.id IS NULL
UNION ALL
SELECT 'modelo_instruccion: modelo_campana_id', COUNT(*)
FROM modelo_instruccion mi
LEFT JOIN modelo_campana mcp ON mcp.id = mi.modelo_campana_id
WHERE mcp.id IS NULL
UNION ALL
SELECT 'modelo_normativa: modelo_campana_id', COUNT(*)
FROM modelo_normativa mn
LEFT JOIN modelo_campana mcp ON mcp.id = mn.modelo_campana_id
WHERE mcp.id IS NULL
UNION ALL
SELECT 'modelo_recurso: modelo_campana_id', COUNT(*)
FROM modelo_recurso mr
LEFT JOIN modelo_campana mcp ON mcp.id = mr.modelo_campana_id
WHERE mcp.id IS NULL
UNION ALL
SELECT 'documento_version: documento_id', COUNT(*)
FROM documento_version dv
LEFT JOIN documento_interpretativo di ON di.id = dv.documento_id
WHERE di.id IS NULL
UNION ALL
SELECT 'embedding_version: documento_id', COUNT(*)
FROM embedding_version ev
LEFT JOIN documento_interpretativo di ON di.id = ev.documento_id
WHERE di.id IS NULL
UNION ALL
SELECT 'empresa: id', COUNT(*)
FROM empresa e
LEFT JOIN (SELECT id FROM empresa) sub ON sub.id = e.id
WHERE sub.id IS NULL;

\echo '=== 2. NULL checks on critical columns ==='
SELECT 'articulo: texto IS NULL' AS null_check, COUNT(*) AS violations
FROM articulo WHERE texto IS NULL OR texto = ''
UNION ALL
SELECT 'norma: texto_completo IS NULL', COUNT(*)
FROM norma WHERE texto_completo IS NULL
UNION ALL
SELECT 'aeat_modelo: codigo IS NULL', COUNT(*)
FROM aeat_modelo WHERE codigo IS NULL OR codigo = ''
UNION ALL
SELECT 'aeat_modelo: nombre IS NULL', COUNT(*)
FROM aeat_modelo WHERE nombre IS NULL OR nombre = ''
UNION ALL
SELECT 'aeat_modelo: impuesto IS NULL', COUNT(*)
FROM aeat_modelo WHERE impuesto IS NULL OR impuesto = ''
UNION ALL
SELECT 'documento_interpretativo: referencia IS NULL', COUNT(*)
FROM documento_interpretativo WHERE referencia IS NULL OR referencia = ''
UNION ALL
SELECT 'documento_interpretativo: tipo_documento IS NULL', COUNT(*)
FROM documento_interpretativo WHERE tipo_documento IS NULL OR tipo_documento = ''
UNION ALL
SELECT 'sync_log: worker IS NULL', COUNT(*)
FROM sync_log WHERE worker IS NULL OR worker = ''
UNION ALL
SELECT 'modelo_campana: campana IS NULL', COUNT(*)
FROM modelo_campana WHERE campana IS NULL OR campana = ''
UNION ALL
SELECT 'modelo_casilla: codigo IS NULL', COUNT(*)
FROM modelo_casilla WHERE codigo IS NULL OR codigo = ''
UNION ALL
SELECT 'modelo_casilla: etiqueta IS NULL', COUNT(*)
FROM modelo_casilla WHERE etiqueta IS NULL OR etiqueta = '';

\echo '=== 3. Duplicate checks on logical PKs ==='
SELECT 'articulo: (norma_id, numero) duplicates', COUNT(*) - COUNT(DISTINCT (norma_id, numero))
FROM articulo WHERE norma_id IS NOT NULL AND numero IS NOT NULL
UNION ALL
SELECT 'aeat_modelo: codigo duplicates', COUNT(*) - COUNT(DISTINCT codigo)
FROM aeat_modelo WHERE codigo IS NOT NULL
UNION ALL
SELECT 'documento_interpretativo: referencia duplicates', COUNT(*) - COUNT(DISTINCT referencia)
FROM documento_interpretativo WHERE referencia IS NOT NULL
UNION ALL
SELECT 'modelo_articulo: (modelo_id, articulo_id) duplicates', COUNT(*) - COUNT(DISTINCT (modelo_id, articulo_id))
FROM modelo_articulo
UNION ALL
SELECT 'modelo_campana: (modelo_id, campana) duplicates', COUNT(*) - COUNT(DISTINCT (modelo_id, campana))
FROM modelo_campana WHERE modelo_id IS NOT NULL AND campana IS NOT NULL;

\echo '=== Summary ==='
\echo 'All checks completed. Zero violations expected.'
