import httpx

pregunta = "No residente rentas inmobiliarias modelo 216"

print("=== FULLTEXT ONLY (hybrid_weight=0.0) ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': pregunta, 'hybrid_weight': 0.0, 'limit': 15})
data = r.json()
for i, item in enumerate(data.get('resultados', [])[:15], 1):
    print(f"  #{i} norma={item['norma']}:1  rank={item.get('rank')}  score={item.get('rrf_score')}")

print("\n=== PURE VECTOR (hybrid_weight=1.0) ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': pregunta, 'hybrid_weight': 1.0, 'limit': 15})
data = r.json()
for i, item in enumerate(data.get('resultados', [])[:15], 1):
    print(f"  #{i} norma={item['norma']}:1  rank={item.get('rank')}  score={item.get('rrf_score')}")

print("\n=== HYBRID 0.5 ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': pregunta, 'hybrid_weight': 0.5, 'limit': 15})
data = r.json()
for i, item in enumerate(data.get('resultados', [])[:15], 1):
    print(f"  #{i} norma={item['norma']}:1  rank={item.get('rank')}  score={item.get('rrf_score')}  sources={item.get('rrf_sources')}")
