from sqlalchemy import text
from db import db_session

with db_session() as db:
    # Check if search_vector has data for FactA articles
    result = db.execute(text('''
        SELECT n.codigo, a.numero, v.texto IS NOT NULL as has_text,
               LENGTH(v.search_vector) as vector_size
        FROM version_articulo v
        JOIN articulo a ON a.id = v.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE n.codigo IN ('LIVA', 'IRNR', 'LIS', 'ES_US_CONVENIO')
        ORDER BY n.codigo, a.numero
    ''')).mappings()
    
    rows = result.fetchall()
    with_text = sum(1 for r in rows if r['has_text'])
    with_vector = sum(1 for r in rows if r['vector_size'] > 0)
    print(f'Total versiones: {len(rows)}')
    print(f'Con texto: {with_text}')
    print(f'Con search_vector: {with_vector}')
    
    # Check if ts_rank works
    result2 = db.execute(text("SELECT n.codigo, a.numero, LEFT(v.texto, 200) as resumen FROM version_articulo v JOIN articulo a ON a.id = v.articulo_id JOIN norma n ON n.id = a.norma_id WHERE v.search_vector @@ plainto_tsquery('spanish', 'intracomunitaria') ORDER BY ts_rank(v.search_vector, plainto_tsquery('spanish', 'intracomunitaria')) DESC LIMIT 5")).mappings()
    
    rows2 = result2.fetchall()
    print(f'\nBúsqueda ts_rank para intracomunitaria: {len(rows2)} resultados')
    for r in rows2:
        print(f'  {r["codigo"]}:{r["numero"]} - {r["resumen"][:100]}')
