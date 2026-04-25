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
    
    print(f"returns_rows: {leg_rows.returns_rows}")
    
    seen = set()
    count = 0
    for row in leg_rows:
        key = f"{row['norma']}:{row['numero']}"
        if key not in seen:
            seen.add(key)
            texto = row["texto"] or ""
            print(f"  {row['norma']}:{row['numero']} - {texto[:100]}")
            count += 1
    
    print(f"Total unique: {count}")
