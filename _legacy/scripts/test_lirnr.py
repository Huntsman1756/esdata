import httpx
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': 'LIRNR'})
data = r.json()
print('Total:', data.get('total', 'N/A'))
if 'resultados' in data:
    for item in data['resultados'][:5]:
        print(f"  - {item.get('norma')}: {item.get('tipo')}")
elif 'results' in data:
    for item in data['results'][:5]:
        print(f"  - {item.get('norma')}: {item.get('tipo')}")
else:
    print('Keys:', list(data.keys()))
    print('First 500 chars:', str(data)[:500])
