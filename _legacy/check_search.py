import requests, json

# Test the actual API response for a failing query
r = requests.get('http://localhost:8000/v1/legislacion/buscar', params={'q': 'Autoliquidacion trimestral IVA modelo 303'})
data = r.json()
print("=== iva-002: Autoliquidacion trimestral IVA modelo 303 ===")
print(f"Results: {len(data.get('resultados', []))}")
for item in data.get('resultados', []):
    print(f"  norma={item['norma']} art={item['numero']} tipo={item['tipo']} rank={item.get('rank')}")

print()

# Check what the golden expects
import json as j
golden = j.load(open('scripts/golden_queries.json'))
for q in golden['queries']:
    if q['id'] == 'iva-002':
        print(f"Expected fuente: {q['criterios'].get('fuente_esperada')}")
        print(f"Expected articulo: {q['criterios'].get('articulo_esperado')}")
        break
