from db import get_db
from sqlalchemy import text
db = next(get_db())

r = list(db.execute(text("SELECT COUNT(*) FROM documento_fragmento cf WHERE cf.search_vector @@ websearch_to_tsquery('spanish', 'pan')")).mappings())
print('Chunks matching pan (tsvector):', r[0]['count'])

r2 = list(db.execute(text("SELECT COUNT(*) FROM documento_fragmento cf WHERE cf.texto ILIKE :t"), {'t': '%pan%'}).mappings())
print('Chunks matching pan (ILIKE):', r2[0]['count'])

r3 = list(db.execute(text("""
SELECT COUNT(*)
FROM documento_fragmento cf
JOIN articulo a ON a.id = cf.documento_origen_id
JOIN norma n ON n.id = a.norma_id
JOIN version_articulo va ON va.articulo_id = a.id
WHERE cf.search_vector @@ websearch_to_tsquery('spanish', 'pan')
AND cf.documento_origen_tipo = 'legislacion'
""")).mappings())
print('With JOINs matching:', r3[0]['count'])

r4 = list(db.execute(text("""
SELECT COUNT(*)
FROM (
    SELECT DISTINCT ON (cf.documento_origen_id)
        cf.documento_origen_id
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    JOIN version_articulo va ON va.articulo_id = a.id
    WHERE cf.search_vector @@ websearch_to_tsquery('spanish', 'pan')
    AND cf.documento_origen_tipo = 'legislacion'
    AND va.vigente_desde = (
        SELECT MAX(v2.vigente_desde)
        FROM version_articulo v2
        JOIN articulo a2 ON v2.articulo_id = a2.id
        WHERE a2.id = a.id
    )
    ORDER BY cf.documento_origen_id, va.vigente_desde DESC
) AS sub
""")).mappings())
print('With vig subquery:', r4[0]['count'])

db.close()
