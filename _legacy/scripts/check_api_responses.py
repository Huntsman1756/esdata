import os, sys

os.environ['DATABASE_URL'] = 'sqlite:///C:/temp/test_esdata.sqlite3'
sys.path.insert(0, 'apps/api/tests')
import conftest
os.environ['DATABASE_URL'] = str(conftest.engine.url)
sys.path.insert(0, 'apps/api')

from fastapi.testclient import TestClient
from main import app
import json

c = TestClient(app, raise_server_exceptions=False)

# Query 1: tipo reducido IVA pan leche libros (should match LIVA art.91)
r = c.get('/v1/consulta', params={'q': 'tipo reducido IVA pan leche libros'})
print('=== /v1/consulta "tipo reducido IVA pan leche libros" ===')
print(f'Status: {r.status_code}')
data = r.json()
print(json.dumps(data, indent=2, ensure_ascii=False)[:4000])

print()
print('='*60)
print()

# Query 2: buscar legislacion directly
r2 = c.get('/v1/legislacion/buscar', params={'q': 'pan leche libros tipo reducido'})
print('=== /v1/legislacion/buscar "pan leche libros tipo reducido" ===')
print(f'Status: {r2.status_code}')
data2 = r2.json()
print(json.dumps(data2, indent=2, ensure_ascii=False)[:4000])

print()
print('='*60)
print()

# Query 3: doctrina
r3 = c.get('/v1/doctrina/buscar', params={'q': 'IVA pan leche'})
print('=== /v1/doctrina/buscar "IVA pan leche" ===')
print(f'Status: {r3.status_code}')
data3 = r3.json()
print(json.dumps(data3, indent=2, ensure_ascii=False)[:4000])
