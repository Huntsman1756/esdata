import httpx

q = "IRNR dividendos retencion modelo 124"

# Fulltext
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': q}, timeout=5)
print(f"=== /buscar ===")
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Total: {len(data.get('resultados', []))}")
    for item in data.get('resultados', [])[:5]:
        print(f"  {item['norma']}:{item.get('numero')}  rank={item.get('rank')}")
else:
    print(f"Body: {r.text[:200]}")

# Hybrid weight=0.0
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': q, 'hybrid_weight': 0.0, 'limit': 5}, timeout=5)
print(f"\n=== hybrid weight=0.0 ===")
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Total: {len(data.get('resultados', []))}")
    for item in data.get('resultados', [])[:5]:
        print(f"  {item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  src={item.get('rrf_sources')}")
else:
    print(f"Body: {r.text[:500]}")

# Hybrid weight=0.5
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': q, 'hybrid_weight': 0.5, 'limit': 5}, timeout=5)
print(f"\n=== hybrid weight=0.5 ===")
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Total: {len(data.get('resultados', []))}")
    for item in data.get('resultados', [])[:5]:
        print(f"  {item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  src={item.get('rrf_sources')}")
else:
    print(f"Body: {r.text[:500]}")
