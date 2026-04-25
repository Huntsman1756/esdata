"""Debug search query execution."""
from services.search import _search_legislacion_pg, _is_postgres
from db import db_session

with db_session() as db:
    print("is_postgres:", _is_postgres(db))
    result = _search_legislacion_pg(db, "irnr", None, None, None, None, None)
    print("resultados:", len(result.get("resultados", [])))
    for r in result.get("resultados", [])[:3]:
        print(f"  {r['norma']} art. {r['numero']}")
