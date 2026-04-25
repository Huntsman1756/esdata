import sys, os
sys.path.insert(0, 'apps/api')
os.environ['DATABASE_URL'] = 'postgresql+psycopg://esdata:testpass@localhost:5434/esdata'

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)

# Test search
r = client.get('/v1/legislacion/buscar', params={'q': 'IRPF modelo 100'})
print(f"IRPF modelo 100: status={r.status_code}")
data = r.json()
print(f"  results: {len(data.get('resultados', []))}")
for item in data.get('resultados', []):
    print(f"  - {item.get('norma')} art. {item.get('numero')}: {item.get('fragmento', '')[:80]}")

# Test IVA
r = client.get('/v1/legislacion/buscar', params={'q': 'IVA pan leche'})
print(f"\nIVA pan leche: status={r.status_code}")
data = r.json()
print(f"  results: {len(data.get('resultados', []))}")
for item in data.get('resultados', []):
    print(f"  - {item.get('norma')} art. {item.get('numero')}: {item.get('fragmento', '')[:80]}")

# Test autoliquidacion
r = client.get('/v1/legislacion/buscar', params={'q': 'autoliquidacion'})
print(f"\nautoliquidacion: status={r.status_code}")
data = r.json()
print(f"  results: {len(data.get('resultados', []))}")
for item in data.get('resultados', []):
    print(f"  - {item.get('norma')} art. {item.get('numero')}: {item.get('fragmento', '')[:80]}")
