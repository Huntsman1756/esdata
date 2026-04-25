import httpx

pregunta = "No residente rentas inmobiliarias modelo 216"

for weight in [0.0, 0.2, 0.3, 0.5, 0.7, 0.8, 1.0]:
    r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': pregunta, 'hybrid_weight': weight})
    data = r.json()
    
    normas = set()
    if 'resultados' in data:
        for item in data['resultados'][:5]:
            if item.get('norma'):
                normas.add(item['norma'])
    
    print(f"hybrid_weight={weight:.1f}: {sorted(normas)[:10]}")

# Also test full-text search only
print("\n=== Full-text search only ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': pregunta})
data = r.json()
normas = set()
if 'resultados' in data:
    for item in data['resultados'][:10]:
        if item.get('norma'):
            normas.add(item['norma'])
print(f"buscar (full-text): {sorted(normas)[:15]}")
