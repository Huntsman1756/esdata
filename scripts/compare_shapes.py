import os, sys
os.environ['DATABASE_URL'] = 'sqlite:///C:/temp/test_esdata.sqlite3'
sys.path.insert(0, 'apps/api/tests')
import conftest
os.environ['DATABASE_URL'] = str(conftest.engine.url)
sys.path.insert(0, 'apps/api')

for mod in list(sys.modules.keys()):
    if 'main' in mod or mod == 'db' or mod.startswith('routers'):
        del sys.modules[mod]

from fastapi.testclient import TestClient
from main import app
import json

c = TestClient(app, raise_server_exceptions=False)

# Golden query 1: "tipo reducido IVA pan leche libros"
r = c.get('/v1/consulta', params={'q': 'tipo reducido IVA pan leche libros'})
data = r.json()

print('=== /v1/consulta keys ===')
print(list(data.keys()))

print()
print('=== consulta.modelos[0] keys ===')
if data.get('modelos'):
    print(list(data['modelos'][0].keys()))
    print(f"  norma_base: {data['modelos'][0].get('norma_base')}")

print()
print('=== consulta.normativa[0] keys ===')
if data.get('normativa'):
    print(list(data['normativa'][0].keys()))
    print(json.dumps(data['normativa'][0], indent=2, ensure_ascii=False)[:500])
else:
    print('  (vacío)')

print()
print('=== consulta.resultados ===')
if data.get('resultados'):
    print(f"  count: {len(data['resultados'])}")
    print(f"  keys: {list(data['resultados'][0].keys())}")
    print(f"  [0].norma: {data['resultados'][0].get('norma')}")
    print(f"  [0].articulo: {data['resultados'][0].get('articulo')}")
else:
    print('  (vacío)')

print()
print('=== consulta.obligacion ===')
if data.get('obligacion'):
    print(json.dumps(data['obligacion'][:1], indent=2, ensure_ascii=False)[:500])
else:
    print('  (vacío)')

print()
print('=== consulta.doctrina ===')
if data.get('doctrina'):
    print(f"  count: {len(data['doctrina'])}")
    print(f"  keys: {list(data['doctrina'][0].keys())}")
    print(json.dumps(data['doctrina'][:1], indent=2, ensure_ascii=False)[:500])
else:
    print('  (vacío)')

# Golden query doctrinal: "IVA dividendos"
print()
print('='*60)
print('=== /v1/doctrina/buscar "IVA dividendos" ===')
r2 = c.get('/v1/doctrina/buscar', params={'q': 'IVA dividendos'})
data2 = r2.json()
print(f"  resultados: {len(data2.get('resultados', []))}")
if data2.get('resultados'):
    print(f"  keys: {list(data2['resultados'][0].keys())}")
    print(json.dumps(data2['resultados'][:1], indent=2, ensure_ascii=False)[:500])

# Golden query buscar: "renta no residente IRNR"
print()
print('='*60)
print('=== /v1/legislacion/buscar "renta no residente IRNR" ===')
r3 = c.get('/v1/legislacion/buscar', params={'q': 'renta no residente IRNR'})
data3 = r3.json()
print(f"  resultados: {len(data3.get('resultados', []))}")
if data3.get('resultados'):
    print(f"  keys: {list(data3['resultados'][0].keys())}")
    print(json.dumps(data3['resultados'][:1], indent=2, ensure_ascii=False)[:500])
