import httpx
import json

# Get all norms from DB via list endpoint
r = httpx.get('http://localhost:8001/v1/legislacion/normas')
print("=== /v1/legislacion/normas ===")
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")

# Try get_norma endpoint
print("\n=== /v1/legislacion/norma/{codigo} ===")
for codigo in ['LGT', 'LIRPF', 'LIVA', 'IRNR', 'DAC6']:
    r = httpx.get(f'http://localhost:8001/v1/legislacion/norma/{codigo}')
    print(f"  {codigo}: {r.status_code} - {r.text[:200]}")

# Try buscar with different params
print("\n=== Buscar con filtro por norma ===")
for codigo in ['LGT', 'LIRPF', 'LIVA', 'IRNR']:
    r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': 'articulo', 'norma': codigo})
    data = r.json()
    total = data.get('total', 0) if isinstance(data, dict) else 'N/A'
    print(f"  norma={codigo}: total={total}")
