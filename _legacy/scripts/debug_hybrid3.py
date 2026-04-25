import httpx

pregunta = "No residente rentas inmobiliarias modelo 216"

# Test fulltext search via /buscar (non-hybrid)
print("=== Fulltext via /v1/legislacion/buscar ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': pregunta}, timeout=10)
data = r.json()
normas = set()
for item in data.get('resultados', [])[:10]:
    normas.add(item.get('norma'))
print(f"  Normas: {sorted(normas)[:10]}")
print(f"  Total: {data.get('total', 'N/A')}")

# Test hybrid with small weight
print("\n=== Hybrid hybrid_weight=0.1 ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': pregunta, 'hybrid_weight': 0.1, 'limit': 15}, timeout=30)
data = r.json()
for i, item in enumerate(data.get('resultados', [])[:15], 1):
    print(f"  #{i} norma={item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  sources={item.get('rrf_sources')}")

# Test hybrid with weight 0.2
print("\n=== Hybrid hybrid_weight=0.2 ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': pregunta, 'hybrid_weight': 0.2, 'limit': 15}, timeout=30)
data = r.json()
for i, item in enumerate(data.get('resultados', [])[:15], 1):
    print(f"  #{i} norma={item['norma']}:{item.get('numero')}  rrf={item.get('rrf_score')}  sources={item.get('rrf_sources')}")
