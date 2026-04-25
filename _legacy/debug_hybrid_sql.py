import sys; sys.path.insert(0, 'apps/api')
from sqlalchemy import text
from db import db_session

# Test what the hybrid SQL actually returns
with db_session() as db:
    q = 'IRNR dividendos retencion modelo 124'
    
    # Build tsquery like hybrid does
    from services.search import _build_tsquery_sql
    tsquery_str, extra_or = _build_tsquery_sql(q)
    full_tsq = f"({tsquery_str})"
    
    print("=== Hybrid-style tsquery ===")
    print(f"tsquery_str: {tsquery_str[:300]}...")
    print()
    
    # Execute the exact hybrid query
    params = {}
    params.update(extra_or)
    params["limit"] = 20
    
    search_filter = f"cf.search_vector @@ {full_tsq}"
    rank_expr = f"ts_rank(cf.search_vector, {full_tsq})"
    
    from services.search import _build_common_filters
    common_filters = _build_common_filters(None, None, None, None, None, params)
    common_filters.append(search_filter)
    where_clause = " AND ".join(common_filters)
    
    vig_subquery = (
        "SELECT MAX(v2.vigente_desde) "
        "FROM version_articulo v2 "
        "JOIN articulo a2 ON v2.articulo_id = a2.id "
        "WHERE a2.id = cf.documento_origen_id"
    )
    
    query = text(f"""
        SELECT DISTINCT ON (cf.documento_origen_id)
            cf.documento_origen_id AS doc_id,
            n.codigo,
            a.numero,
            {rank_expr} AS rank,
            cf.texto AS chunk_texto
        FROM documento_fragmento cf
        JOIN articulo a ON a.id = cf.documento_origen_id
        JOIN norma n ON n.id = a.norma_id
        JOIN version_articulo va ON va.articulo_id = a.id
        WHERE {where_clause}
          AND cf.documento_origen_tipo = 'legislacion'
          AND va.vigente_desde = ({vig_subquery})
        ORDER BY cf.documento_origen_id, rank DESC
        LIMIT :limit
    """)
    
    rows = db.execute(query, params).mappings()
    results = list(rows)
    print(f"Hybrid query returned {len(results)} results")
    for r in results[:10]:
        print(f"  {r['codigo']}:{r['numero']}  rank={r['rank']}")
    
    print()
    print("=== Now testing websearch_to_tsquery ===")
    
    # Test with websearch_to_tsquery (what the normal search uses)
    params2 = {"tsquery": q, "limit": 20}
    search_filter2 = "cf.search_vector @@ websearch_to_tsquery('spanish', :tsquery)"
    rank_expr2 = "ts_rank(cf.search_vector, websearch_to_tsquery('spanish', :tsquery))"
    
    common_filters2 = _build_common_filters(None, None, None, None, None, params2)
    common_filters2.append(search_filter2)
    where_clause2 = " AND ".join(common_filters2)
    
    query2 = text(f"""
        SELECT DISTINCT ON (cf.documento_origen_id)
            cf.documento_origen_id AS doc_id,
            n.codigo,
            a.numero,
            {rank_expr2} AS rank,
            cf.texto AS chunk_texto
        FROM documento_fragmento cf
        JOIN articulo a ON a.id = cf.documento_origen_id
        JOIN norma n ON n.id = a.norma_id
        JOIN version_articulo va ON va.articulo_id = a.id
        WHERE {where_clause2}
          AND cf.documento_origen_tipo = 'legislacion'
          AND va.vigente_desde = ({vig_subquery})
        ORDER BY cf.documento_origen_id, rank DESC
        LIMIT :limit
    """)
    
    rows2 = db.execute(query2, params2).mappings()
    results2 = list(rows2)
    print(f"websearch_to_tsquery returned {len(results2)} results")
    for r in results2[:10]:
        print(f"  {r['codigo']}:{r['numero']}  rank={r['rank']}")
