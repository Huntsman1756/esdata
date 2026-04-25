import httpx

# Test fallback search (version_articulo)
r = httpx.get(
    'http://localhost:8001/v1/legislacion/buscar',
    params={'q': 'mecanismos transfronterizos'},
    timeout=10
)
print(f'Status: {r.status_code}')
d = r.json()
results = d.get('resultados', [])
print(f'Results: {len(results)}')
for res in results[:5]:
    print(f'  norma={res["norma"]} articulo={res["numero"]} rank={res.get("rank")}')

# Test with IRPF (should return 0)
r = httpx.get(
    'http://localhost:8001/v1/legislacion/buscar',
    params={'q': 'IRPF modelo 100'},
    timeout=10
)
d = r.json()
results = d.get('resultados', [])
print(f'\nIRPF results: {len(results)}')

# List all available norms
r = httpx.get('http://localhost:8001/v1/legislacion', timeout=10)
d = r.json()
print(f'\nAvailable norms:')
for n in d.get('normas', []):
    print(f'  {n["codigo"]:15s} {n["titulo"][:60]}')
