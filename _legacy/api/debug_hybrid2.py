import httpx

# Test 1: Fulltext via /buscar con query que tiene abreviaturas
q = "IRNR dividendos retencion modelo 124"
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': q}, timeout=10)
data = r.json()
print(f"=== /buscar '{q}' ===")
print(f"Total: {len(data.get('resultados', []))}")
for i, item in enumerate(data.get('resultados', [])[:5], 1):
    print(f"  #{i} {item['norma']}:{item.get('numero')}  rank={item.get('rank')}")

# Test 2: Hybrid con weight=0.0 (solo fulltext)
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': q, 'hybrid_weight': 0.0, 'limit': 5}, timeout=10)
data = r.json()
print(f"\n=== hybrid weight=0.0 '{q}' ===")
print(f"Total: {len(data.get('resultados', []))}")
for i, item in enumerate(data.get('resultados', [])[:5], 1):
    print(f"  #{i} {item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  src={item.get('rrf_sources')}")

# Test 3: Hybrid con weight=0.5
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': q, 'hybrid_weight': 0.5, 'limit': 5}, timeout=10)
data = r.json()
print(f"\n=== hybrid weight=0.5 '{q}' ===")
print(f"Total: {len(data.get('resultados', []))}")
for i, item in enumerate(data.get('resultados', [])[:5], 1):
    print(f"  #{i} {item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  src={item.get('rrf_sources')}")

# Test 4: Simple query
q2 = "IVA"
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': q2}, timeout=10)
data = r.json()
print(f"\n=== /buscar '{q2}' ===")
print(f"Total: {len(data.get('resultados', []))}")
for i, item in enumerate(data.get('resultados', [])[:5], 1):
    print(f"  #{i} {item['norma']}:{item.get('numero')}  rank={item.get('rank')}")

r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': q2, 'hybrid_weight': 0.0, 'limit': 5}, timeout=10)
data = r.json()
print(f"\n=== hybrid weight=0.0 '{q2}' ===")
print(f"Total: {len(data.get('resultados', []))}")
for i, item in enumerate(data.get('resultados', [])[:5], 1):
    print(f"  #{i} {item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  src={item.get('rrf_sources')}")
