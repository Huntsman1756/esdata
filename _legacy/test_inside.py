from sqlalchemy import text
from db import db_session

with db_session() as db:
    q = "entregas intracomunitarias"
    
    leg_rows = db.execute(text("""
        SELECT a.tipo, n.codigo as norma, a.numero, v.texto,
               v.vigente_desde, v.vigente_hasta,
               ts_rank(v.search_vector, plainto_tsquery('spanish', :q)) AS rank
        FROM version_articulo v
        JOIN articulo a ON a.id = v.articulo_id
        JOIN norma n ON n.id = a.norma_id
        WHERE v.search_vector @@ plainto_tsquery('spanish', :q)
        ORDER BY rank DESC
        LIMIT 10
    """), {"q": q}).mappings()
    
    rows_list = leg_rows.fetchall()
    seen = set()
    for row in rows_list:
        key = f"{row['norma']}:{row['numero']}"
        if key not in seen:
            seen.add(key)
            texto = row["texto"] or ""
            print(f"  [{row['norma']}:{row['numero']}] {texto[:150]}...")
    
    print(f"\nTotal normativa: {len(seen)}")
