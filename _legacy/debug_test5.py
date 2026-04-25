import sys
sys.path.insert(0, '/app')

from db import db_session
from sqlalchemy import text
from services.search import _build_tsquery_sql, _extract_norma_from_query, _add_accents, _build_common_filters

q = 'IRNR rentas sin establecimiento permanente'
norma = _extract_norma_from_query(q)
tsquery_str, tsq_params = _build_tsquery_sql(q)

print('=== DEBUG ===')
print('q:', q)
print('norma detected:', norma)
print('tsquery_str:', tsquery_str)
print('tsq_params:', tsq_params)

with db_session() as db:
    params = {}
    
    # Build common filters
    common_filters = _build_common_filters(norma, None, None, None, None, params)
    print('common_filters:', common_filters)
    print('params after common_filters:', params)
    
    # Build search filter
    if tsquery_str:
        full_tsq = f"({tsquery_str})"
        search_filter = f"cf.search_vector @@ {full_tsq}"
        print('search_filter:', search_filter)
    else:
        search_filter = "cf.texto ILIKE :term"
        params["term"] = f"%{q}%"
    
    common_filters.append(search_filter)
    where_clause = " AND ".join(common_filters)
    print('where_clause:', where_clause)
    
    # Build vig_subquery
    vig_subquery_where = "a2.id = a.id"
    vig_subquery = (
        "SELECT MAX(v2.vigente_desde) "
        "FROM version_articulo v2 "
        "JOIN articulo a2 ON v2.articulo_id = a2.id "
        f"WHERE {vig_subquery_where}"
    )
    
    query = text(
        f"""
        SELECT * FROM (
            SELECT DISTINCT ON (cf.documento_origen_id)
                cf.documento_origen_id AS doc_id,
                n.codigo,
                a.numero,
                a.tipo,
                va.texto,
                va.vigente_desde,
                va.vigente_hasta,
                ts_rank(cf.search_vector, {full_tsq}) AS rank,
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
            WHERE """
        + where_clause
        + f"""
                AND cf.documento_origen_tipo = 'legislacion'
                AND va.vigente_desde = ({vig_subquery})
            ORDER BY cf.documento_origen_id, rank DESC, va.vigente_desde DESC
        ) AS sub
        ORDER BY rank DESC
        LIMIT 10
        """
    )
    
    print('\n=== FULL SQL ===')
    print(query)
    print('\n=== PARAMS ===')
    print(params)
    
    rows = db.execute(query, params, execution_options={"literal_binds": True}).mappings()
    results = list(rows)
    print(f'\n=== RESULTS: {len(results)} rows ===')
    for row in results[:5]:
        print('  ', dict(row))
