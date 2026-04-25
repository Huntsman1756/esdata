import sys, os
sys.path.insert(0, 'apps/api/tests')
import conftest
os.environ['DATABASE_URL'] = str(conftest.engine.url)
for mod in list(sys.modules.keys()):
    if 'main' in mod or mod == 'db' or mod.startswith('routers'):
        del sys.modules[mod]
sys.path.insert(0, 'apps/api')
from fastapi.testclient import TestClient
from main import app
import re

c = TestClient(app, raise_server_exceptions=False)
r = c.get('/v1/consulta', params={'q': 'tipo reducido IVA pan leche libros'})
data = r.json()

# Simular _extraer_fuentes
fuentes = set()
for m in data.get('modelos', []):
    norma_base = m.get('norma_base', '')
    if norma_base:
        match = re.match(r'^([A-Z]+)', norma_base)
        if match:
            fuentes.add(match.group(1))
            print(f"  modelo: {m['codigo']} -> norma_base={norma_base} -> extraido={match.group(1)}")

for r2 in data.get('resultados', []):
    if r2.get('norma'):
        fuentes.add(r2['norma'])

print(f"fuentes extraidas: {fuentes}")
print(f"esperadas: ['LIVA']")
print(f"acierto: {any(f in fuentes for f in ['LIVA'])}")

# Check query irpf-001
print("\n--- irpf-001 ---")
r2 = c.get('/v1/consulta', params={'q': 'Declaracion anual IRPF modelo 100'})
data2 = r2.json()
print(f"keys: {list(data2.keys())}")
print(f"modelos: {len(data2.get('modelos', []))}")
for m in data2.get('modelos', []):
    print(f"  modelo: {m['codigo']} norma_base={m.get('norma_base')}")

# Check query int-001
print("\n--- int-001 ---")
r3 = c.get('/v1/consulta', params={'q': 'No residente rentas inmobiliarias modelo 216'})
data3 = r3.json()
print(f"keys: {list(data3.keys())}")
print(f"modelos: {len(data3.get('modelos', []))}")
for m in data3.get('modelos', []):
    print(f"  modelo: {m['codigo']} norma_base={m.get('norma_base')}")

# Check query comp-001
print("\n--- comp-001 ---")
r4 = c.get('/v1/consulta', params={'q': 'Comunicacion indicio blanqueo capitales modelo 19 SEPBLAC'})
data4 = r4.json()
print(f"keys: {list(data4.keys())}")
print(f"modelos: {len(data4.get('modelos', []))}")
print(f"obligacion: {data4.get('obligacion')}")
for m in data4.get('modelos', []):
    print(f"  modelo: {m['codigo']} norma_base={m.get('norma_base')}")

# Check query mix-005
print("\n--- mix-005 (tasas locales) ---")
r5 = c.get('/v1/consulta', params={'q': 'Tasas locales hacendarias municipales'})
data5 = r5.json()
print(f"keys: {list(data5.keys())}")
print(f"modelos: {len(data5.get('modelos', []))}")
print(f"resultados: {len(data5.get('resultados', []))}")
for m in data5.get('modelos', []):
    print(f"  modelo: {m['codigo']} norma_base={m.get('norma_base')}")
for i, res in enumerate(data5.get('resultados', [])):
    print(f"  resultado[{i}]: norma={res.get('norma')} codigo={res.get('codigo')}")
