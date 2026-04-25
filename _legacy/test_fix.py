import requests
s = requests.Session()
resp = s.get('http://localhost:8001/v1/consulta', params={'q': 'entregas intracomunitarias'})
data = resp.json()
print(f"Total: {data.get('total_resultados', 0)}")
for r in data.get('resultados', []):
    print(f"  [{r['tipo']}] {r.get('norma', r.get('codigo', ''))}:{r.get('articulo', '')}")
    txt = r.get('texto', r.get('fragmento', ''))[:100]
    if txt:
        print(f"    {txt}...")
