import sys; sys.path.insert(0, 'apps/api')
import httpx

# Compare fulltext vs hybrid for the same query
q = "IRNR dividendos retencion modelo 124"

# Fulltext only via /buscar
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': q}, timeout=10)
data = r.json()
print(f"=== FULLTEXT /buscar: '{q}' ===")
print(f"Total: {len(data.get('resultados', []))}")
for i, item in enumerate(data.get('resultados', [])[:10], 1):
    print(f"  #{i} {item['norma']}:{item.get('numero')}  rank={item.get('rank')}")

# Hybrid with weight 0.0 (should be fulltext only)
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': q, 'hybrid_weight': 0.0, 'limit': 10}, timeout=10)
data = r.json()
print(f"\n=== HYBRID weight=0.0: '{q}' ===")
print(f"Total: {len(data.get('resultados', []))}")
for i, item in enumerate(data.get('resultados', [])[:10], 1):
    print(f"  #{i} {item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  src={item.get('rrf_sources')}")

# Hybrid with weight 0.5
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': q, 'hybrid_weight': 0.5, 'limit': 10}, timeout=10)
data = r.json()
print(f"\n=== HYBRID weight=0.5: '{q}' ===")
print(f"Total: {len(data.get('resultados', []))}")
for i, item in enumerate(data.get('resultados', [])[:10], 1):
    print(f"  #{i} {item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  src={item.get('rrf_sources')}")

# Test what websearch_to_tsquery produces for this query
from sqlalchemy import text
from db import db_session
with db_session() as db:
    # What does websearch_to_tsquery return?
    result = db.execute(text("SELECT websearch_to_tsquery('spanish', 'IRNR dividendos retencion modelo 124')")).scalar()
    print(f"\n=== websearch_to_tsquery output: {result} ===")
