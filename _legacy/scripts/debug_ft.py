import httpx

# Test fulltext directly via /buscar
pregunta = "No residente rentas inmobiliarias"

print("=== Fulltext /buscar direct ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': pregunta}, timeout=10)
data = r.json()
print(f"  Total: {data.get('total', 'N/A')}")
for i, item in enumerate(data.get('resultados', [])[:10], 1):
    print(f"  #{i} norma={item['norma']}:{item.get('numero')}  rank={item.get('rank')}")

# Test with simpler query
print("\n=== Fulltext /buscar 'IRNR' ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': 'IRNR'}, timeout=10)
data = r.json()
print(f"  Total: {data.get('total', 'N/A')}")
for i, item in enumerate(data.get('resultados', [])[:10], 1):
    print(f"  #{i} norma={item['norma']}:{item.get('numero')}  rank={item.get('rank')}")

# Test with 'renta inmobiliaria'
print("\n=== Fulltext /buscar 'renta inmobiliaria' ===")
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': 'renta inmobiliaria'}, timeout=10)
data = r.json()
print(f"  Total: {data.get('total', 'N/A')}")
for i, item in enumerate(data.get('resultados', [])[:10], 1):
    print(f"  #{i} norma={item['norma']}:{item.get('numero')}  rank={item.get('rank')}")
