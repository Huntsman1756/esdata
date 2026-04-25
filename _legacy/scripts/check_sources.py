import httpx
import json

# Get all norms from DB
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': 'articulo'})
print("Testing DB norms...")

# Load golden dataset
with open('scripts/golden_queries.json', encoding='utf-8') as f:
    golden = json.load(f)

# Collect all expected sources
expected_sources = set()
for q in golden['queries']:
    for s in q.get('criterios', {}).get('fuente_esperada', []):
        expected_sources.add(s)

print(f"\nFuentes esperadas en golden dataset ({len(expected_sources)}):")
for s in sorted(expected_sources):
    print(f"  {s}")

# Test each source against DB
print("\n--- Testing each source in DB ---")
for source in sorted(expected_sources):
    r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': source})
    data = r.json()
    normas = set()
    if 'resultados' in data:
        for item in data['resultados'][:20]:
            if item.get('norma'):
                normas.add(item['norma'])
    elif 'results' in data:
        for item in data['results'][:20]:
            if item.get('norma'):
                normas.add(item['norma'])
    
    found = bool(normas)
    status = "OK" if found else "MISSING"
    print(f"  {source:15s} -> [{status}] {sorted(normas)[:10]}")
