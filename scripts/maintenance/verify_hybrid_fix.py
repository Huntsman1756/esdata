import sys; sys.path.insert(0, 'apps/api')
from services.search import _build_tsquery_sql, _add_accents
import httpx

# 1. What does _build_tsquery_sql produce for the failing queries?
queries = [
    "No residente rentas inmobiliarias modelo 216",
    "IRNR dividendos retencion modelo 124",
    "IRNR ganancias patrimoniales no residentes",
    "Resumen anual retenciones IRNR modelo 296",
]

for q in queries:
    tsq, extra = _build_tsquery_sql(q)
    print(f"Query: {q}")
    print(f"  tsquery: {tsq[:200]}..." if tsq and len(tsq) > 200 else f"  tsquery: {tsq}")
    print(f"  extra: {extra}")
    print()

# 2. Test hybrid for each failing query
print("=== HYBRID RESULTS ===")
for q in queries:
    r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', 
                  params={'q': q, 'hybrid_weight': 0.5, 'limit': 10}, timeout=30)
    data = r.json()
    normas = set()
    for item in data.get('resultados', [])[:10]:
        normas.add(item.get('norma'))
    sources = set()
    for item in data.get('resultados', []):
        sources.update(item.get('rrf_sources', []))
    print(f"Query: {q}")
    print(f"  Total: {len(data.get('resultados', []))}")
    print(f"  Normas: {sorted(normas)[:10]}")
    print(f"  Sources: {sources}")
    for i, item in enumerate(data.get('resultados', [])[:5], 1):
        print(f"    #{i} {item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  src={item.get('rrf_sources')}")
    print()
