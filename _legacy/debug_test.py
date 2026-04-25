import requests

r = requests.get('http://localhost:8000/legislacion/buscar', params={'q': 'IRNR rentas sin establecimiento permanente'})
data = r.json()
print('IRNR results:', len(data.get('resultados', [])))
for x in data.get('resultados', [])[:5]:
    print('  ', x['norma'], 'art.', x['numero'], x.get('fragmento', '')[:80])
