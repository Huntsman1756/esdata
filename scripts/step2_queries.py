"""Paso 2: Ejecutar queries manuales contra endpoints y guardar JSON real."""
import os, sys, json

os.environ['DATABASE_URL'] = 'sqlite:///G:/_Proyectos/esdata/apps/api/tests/test_esdata.sqlite3'
sys.path.insert(0, 'G:/_Proyectos/esdata/apps/api/tests')
import conftest
os.environ['DATABASE_URL'] = str(conftest.engine.url)
sys.path.insert(0, 'G:/_Proyectos/esdata/apps/api')

# Limpiar caches
for mod in list(sys.modules.keys()):
    if 'main' in mod or mod == 'db' or mod.startswith('routers'):
        del sys.modules[mod]

from fastapi.testclient import TestClient
from main import app

c = TestClient(app, raise_server_exceptions=False)

queries = {
    'consulta_pan': '/v1/consulta?q=tipo%20reducido%20IVA%20pan%20leche%20libros',
    'buscar_pan': '/v1/legislacion/buscar?q=pan',
    'buscar_irnr': '/v1/legislacion/buscar?q=renta%20no%20residente',
    'doctrina_dividendo': '/v1/doctrina/buscar?q=IVA%20dividendos',
    'doctrina_liva': '/v1/doctrina/buscar?q=LIVA',
    'consulta_irnr': '/v1/consulta?q=renta%20no%20residente%20IRNR',
}

results = {}
for name, url in queries.items():
    r = c.get(url)
    results[name] = {
        'status': r.status_code,
        'json': r.json(),
    }
    print(f'=== {name} ({r.status_code}) ===')
    print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:800])
    print()

# Guardar para análisis
with open('G:/_Proyectos/esdata/scripts/api_responses.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
print('Guardado en api_responses.json')
