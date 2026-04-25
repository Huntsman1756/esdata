import sys
sys.path.insert(0, '/app')

from db import db_session
from sqlalchemy import text
from services.search import _build_tsquery_sql, _extract_norma_from_query, _build_common_filters

q = 'IRNR rentas sin establecimiento permanente'
norma = _extract_norma_from_query(q)
tsquery_str, tsq_params = _build_tsquery_sql(q)

print('norma:', norma)
print('tsquery:', tsquery_str)

with db_session() as db:
    params = {}
    common_filters = _build_common_filters(norma, None, None, None, None, params)
    search_filter = f"cf.search_vector @@ ({tsquery_str})"
    where_clause = " AND ".join(common_filters + [search_filter])
    
    vig_subquery = "SELECT MAX(v2.vigente_desde) FROM version_articulo v2 JOIN articulo a2 ON v2.articulo_id = a2.id WHERE a2.id = a.id"
    
    sql = f"""
    SELECT cf.documento_origen_id, n.codigo, a.numero, a.tipo,
           ts_rank(cf.search_vector, ({tsquery_str})) AS rank
    FROM documento_fragmento cf
    JOIN articulo a ON a.id = cf.documento_origen_id
    JOIN norma n ON n.id = a.norma_id
    JOIN version_articulo va ON va.articulo_id = a.id
    WHERE {where_clause}
      AND cf.documento_origen_tipo = 'legislacion'
      AND va.vigente_desde = ({vig_subquery})
    ORDER BY rank DESC
    LIMIT 5
    """
    
    print('\nSQL:')
    print(sql)
    print('\nParams:', params)
    
    result = db.execute(text(sql), params, execution_options={"literal_binds": True})
    rows = result.fetchall()
    print(f'\nRows: {len(rows)}')
    for row in rows:
        print(' ', dict(row))
