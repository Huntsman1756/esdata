import os, sys
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql+psycopg://esdata:esdata_dev@postgres:5432/esdata').replace('postgresql+psycopg://', 'postgresql://')
from db import get_db
from sqlalchemy import text
db = next(get_db())

# Full query like in search.py
query = text("""
    SELECT * FROM (
        SELECT DISTINCT ON (cf.documento_origen_id)
            cf.documento_origen_id AS doc_id,
            n.codigo,
            a.numero,
            a.tipo,
            va.texto,
            va.vigente_desde,
            va.vigente_hasta,
            ts_rank(cf.search_vector, websearch_to_tsquery('spanish', 'pan')) AS rank,
            cf.texto AS chunk_texto,
            cf.id AS chunk_id,
            cf.chunk_type,
            cf.titulo AS chunk_titulo,
            n.boe_id,
            n.eli_uri
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
        ORDER BY cf.documento_origen_id, rank DESC, va.vigente_desde DESC
    ) AS sub
    ORDER BY rank DESC
    LIMIT 10
""")

rows = list(db.execute(query).mappings())
print(f'Rows returned: {len(rows)}')
for r in rows:
    print(f'  doc_id={r["doc_id"]}, norma={r["codigo"]}, numero={r["numero"]}, rank={r["rank"]}')
    if not rows:
        print('  (empty)')

# Check what the DISTINCT ON sees
print()
print('--- Distinct ON check ---')
r2 = list(db.execute(text("""
    SELECT DISTINCT ON (cf.documento_origen_id)
        cf.documento_origen_id AS doc_id,
        n.codigo,
        a.numero,
        ts_rank(cf.search_vector, websearch_to_tsquery('spanish', 'pan')) AS rank
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
    ORDER BY cf.documento_origen_id, rank DESC, va.vigente_desde DESC
""")).mappings())
print(f'DISTINCT ON rows: {len(r2)}')
for r in r2:
    print(f'  doc_id={r["doc_id"]}, norma={r["codigo"]}, numero={r["numero"]}, rank={r["rank"]}')

# Check what the vig subquery returns
print()
print('--- Vig subquery check ---')
r3 = list(db.execute(text("""
    SELECT a.id, a.numero, va.vigente_desde,
           (SELECT MAX(v2.vigente_desde) FROM version_articulo v2 JOIN articulo a2 ON v2.articulo_id = a2.id WHERE a2.id = a.id) AS max_vigente
    FROM articulo a
    JOIN version_articulo va ON va.articulo_id = a.id
    WHERE va.vigente_desde = (
        SELECT MAX(v2.vigente_desde)
        FROM version_articulo v2
        JOIN articulo a2 ON v2.articulo_id = a2.id
        WHERE a2.id = a.id
    )
    LIMIT 5
""")).mappings())
print('Vig subquery samples:')
for r in r3:
    print(f'  art_id={r["id"]}, numero={r["numero"]}, vigente_desde={r["vigente_desde"]}, max_vigente={r["max_vigente"]}, match={r["vigente_desde"] == r["max_vigente"]}')

db.close()
