import os, sys

# Simular lo que hace TestClient: importar main sin haber seteado DATABASE_URL
# primero
print('=== Simulacion TestClient (sin pre-set DATABASE_URL) ===')
# Limpiar cache de modulos
for mod in list(sys.modules.keys()):
    if 'esdata' in mod or 'db' in mod or 'main' in mod or 'search' in mod:
        del sys.modules[mod]

# Ahora importar main directamente (como lo hace TestClient)
os.environ['DATABASE_URL'] = 'sqlite:///C:/temp/test_esdata.sqlite3'
sys.path.insert(0, 'apps/api/tests')
import conftest

# Limpiar de nuevo
for mod in list(sys.modules.keys()):
    if 'esdata' in mod or 'db' in mod or 'main' in mod or 'search' in mod:
        del sys.modules[mod]

# Setear DATABASE_URL ANTES de importar main
os.environ['DATABASE_URL'] = str(conftest.engine.url)
print(f'DATABASE_URL set: {os.environ["DATABASE_URL"]}')

sys.path.insert(0, 'apps/api')
from db import engine
print(f'Engine URL: {engine.url}')

from services.search import search_legislacion
r = search_legislacion('pan')
print(f'Resultados "pan": {len(r.get("resultados", []))}')
