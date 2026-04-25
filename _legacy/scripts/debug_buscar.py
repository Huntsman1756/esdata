import os, sys
os.environ['DATABASE_URL'] = 'sqlite:///C:/temp/test_esdata.sqlite3'
sys.path.insert(0, 'apps/api/tests')
import conftest
os.environ['DATABASE_URL'] = str(conftest.engine.url)
sys.path.insert(0, 'apps/api')

from services.search import search_legislacion
import json

# Test IRNR
print('=== search_legislacion("renta no residente") ===')
r = search_legislacion('renta no residente')
print(f'  resultados: {len(r.get("resultados", []))}')
for res in r.get('resultados', []):
    print(f"    {res['norma']}.{res['numero']}: {res['confianza']['fuentes']}")

print()
print('=== search_legislacion("no residentes") ===')
r2 = search_legislacion('no residentes')
print(f'  resultados: {len(r2.get("resultados", []))}')
for res in r2.get('resultados', []):
    print(f"    {res['norma']}.{res['numero']}: {res['confianza']['fuentes']}")

print()
print('=== search_legislacion("dividendos") ===')
r3 = search_legislacion('dividendos')
print(f'  resultados: {len(r3.get("resultados", []))}')
for res in r3.get('resultados', []):
    print(f"    {res['norma']}.{res['numero']}: {res['confianza']['fuentes']}")

print()
print('=== search_legislacion("pan") ===')
r4 = search_legislacion('pan')
print(f'  resultados: {len(r4.get("resultados", []))}')
for res in r4.get('resultados', []):
    print(f"    {res['norma']}.{res['numero']}: {res['confianza']['fuentes']}")
