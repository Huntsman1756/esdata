import sys
sys.path.insert(0, 'apps/api')

from db import db_session
from services.search import _build_tsquery_sql

# Test what _build_tsquery_sql generates
q = "IRNR dividendos retencion modelo 124"
tsq, extra = _build_tsquery_sql(q)
print(f"Query: {q}")
print(f"tsquery: {tsq}")
print(f"extra: {extra}")

# Now test the actual SQL execution
with db_session() as db:
    # Test plainto_tsquery directly
    result = db.execute(
        db.text("SELECT plainto_tsquery('spanish', 'irnr')::text")
    ).scalar()
    print(f"\nplainto_tsquery('spanish', 'irnr'): {result}")
    
    result = db.execute(
        db.text("SELECT plainto_tsquery('spanish', 'dividendos')::text")
    ).scalar()
    print(f"plainto_tsquery('spanish', 'dividendos'): {result}")
    
    result = db.execute(
        db.text("SELECT plainto_tsquery('spanish', 'retencion')::text")
    ).scalar()
    print(f"plainto_tsquery('spanish', 'retencion'): {result}")
    
    result = db.execute(
        db.text("SELECT plainto_tsquery('spanish', 'modelo')::text")
    ).scalar()
    print(f"plainto_tsquery('spanish', 'modelo'): {result}")
    
    result = db.execute(
        db.text("SELECT plainto_tsquery('spanish', '124')::text")
    ).scalar()
    print(f"plainto_tsquery('spanish', '124'): {result}")
    
    # Test the full tsquery
    result = db.execute(
        db.text(f"SELECT ({tsq})::text")
    ).scalar()
    print(f"\nFull tsquery: {result}")
    
    # Test search_vector @@ tsquery
    result = db.execute(
        db.text(f"""
            SELECT COUNT(*) FROM documento_fragmento cf
            JOIN articulo a ON a.id = cf.documento_origen_id
            JOIN norma n ON n.id = a.norma_id
            WHERE cf.search_vector @@ ({tsq})
            AND cf.documento_origen_tipo = 'legislacion'
        """)
    ).scalar()
    print(f"documento_fragmento matches: {result}")
    
    # Test with ILIKE as fallback
    result = db.execute(
        db.text("""
            SELECT COUNT(*) FROM documento_fragmento cf
            JOIN articulo a ON a.id = cf.documento_origen_id
            JOIN norma n ON n.id = a.norma_id
            WHERE cf.texto ILIKE '%IRNR%'
            AND cf.documento_origen_tipo = 'legislacion'
        """)
    ).scalar()
    print(f"documento_fragmento ILIKE '%IRNR%': {result}")
    
    # Test with plainto_tsquery for each word that is >= 3 chars
    words = ["dividendos", "retencion", "modelo"]
    parts = [f"plainto_tsquery('spanish', '{w}')" for w in words]
    combined = " || ".join(parts)
    print(f"\nCombined tsquery: {combined}")
    
    result = db.execute(
        db.text(f"""
            SELECT COUNT(*) FROM documento_fragmento cf
            JOIN articulo a ON a.id = cf.documento_origen_id
            JOIN norma n ON n.id = a.norma_id
            WHERE cf.search_vector @@ ({combined})
            AND cf.documento_origen_tipo = 'legislacion'
        """)
    ).scalar()
    print(f"documento_fragmento matches with combined: {result}")
    
    # Test the full query with rank
    result = db.execute(
        db.text(f"""
            SELECT n.codigo, a.numero, ts_rank(cf.search_vector, ({combined})) as rank
            FROM documento_fragmento cf
            JOIN articulo a ON a.id = cf.documento_origen_id
            JOIN norma n ON n.id = a.norma_id
            WHERE cf.search_vector @@ ({combined})
            AND cf.documento_origen_tipo = 'legislacion'
            ORDER BY rank DESC
            LIMIT 10
        """)
    ).mappings()
    print(f"\nFulltext results:")
    for row in result:
        print(f"  {row['codigo']}:{row['numero']}  rank={row['rank']}")
