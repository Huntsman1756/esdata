import sys; sys.path.insert(0, 'apps/api')
from services.search import _build_tsquery_sql, _add_accents
import httpx

pregunta = 'No residente rentas inmobiliarias modelo 216'
print(f'Query: {pregunta}')
print(f'After accents: {_add_accents(pregunta)}')

tsquery_str, extra_or = _build_tsquery_sql(pregunta)
print(f'tsquery_str: {tsquery_str}')
print(f'extra_or: {extra_or}')

# Test hybrid with IRNR
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': 'IRNR', 'hybrid_weight': 0.3, 'limit': 10}, timeout=10)
data = r.json()
print(f'\nHybrid 0.3 IRNR: {len(data.get("resultados", []))} resultados')
for item in data.get('resultados', [])[:10]:
    print(f"  norma={item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  sources={item.get('rrf_sources')}")
