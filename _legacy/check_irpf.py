import httpx, json

r = httpx.get(
    'http://localhost:8001/v1/legislacion/buscar/hybrid',
    params={'q': 'Declaracion anual IRPF modelo 100', 'hybrid_weight': 0.5},
    timeout=30
)
data = r.json()
results = data.get('resultados', [])
print(f'Total results: {len(results)}')
for i, res in enumerate(results[:5]):
    fn = res.get('fuente_norma', '?')
    if fn:
        fn = fn[:60]
    print(f'  [{i}] fuente_norma={fn}')
    print(f'       codigo={res.get("codigo", "?")}')
    ct = res.get('chunk_titulo', '?')
    if ct:
        ct = ct[:80]
    print(f'       chunk_titulo={ct}')
    print(f'       rank={res.get("rank")}')
    print()
