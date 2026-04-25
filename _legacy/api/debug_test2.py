import sys
sys.path.insert(0, '/app')

from db import db_session
from sqlalchemy import text
from services.search import _build_tsquery_sql, _extract_norma_from_query

q = 'IRNR rentas sin establecimiento permanente'
norma = _extract_norma_from_query(q)
tsquery_str, tsq_params = _build_tsquery_sql(q)

print('norma:', norma)
print('tsquery:', tsquery_str)
print('tsq_params:', tsq_params)

with db_session() as db:
    params = {'norma': norma}
    params.update(tsq_params)
    
    sql = "SELECT cf.documento_origen_id, n.codigo, a.numero FROM documento_fragmento cf JOIN articulo a ON a.id = cf.documento_origen_id JOIN norma n ON n.id = a.norma_id WHERE n.codigo = :norma AND cf.search_vector @@ (plainto_tsquery('spanish', :tsq) || plainto_tsquery('spanish', :accents)) AND cf.documento_origen_tipo = 'legislacion' LIMIT 5"
    
    print('SQL:', sql)
    print('params:', params)
    
    result = db.execute(text(sql), params)
    rows = result.fetchall()
    print('rows:', len(rows))
    for row in rows:
        print(' ', row)
