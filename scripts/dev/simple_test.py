import httpx

queries = [
    "IRNR dividendos retencion modelo 124",
    "Impuesto sociedades modelo IS",
    "Obligaciones formales tributarias LGT",
]

for q in queries:
    # Fulltext
    r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': q}, timeout=5)
    ft_normas = [item['norma'] for item in r.json().get('resultados', [])[:5]]
    
    # Hybrid 0.0
    r = httpx.get('http://localhost:8001/v1/legislacion/buscar/hybrid', params={'q': q, 'hybrid_weight': 0.0, 'limit': 5}, timeout=5)
    h0_normas = [item['norma'] for item in r.json().get('resultados', [])[:5]]
    
    print(f"Query: {q}")
    print(f"  /buscar:  {ft_normas}")
    print(f"  hybrid0:  {h0_normas}")
    print()
