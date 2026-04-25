import httpx
q = 'Transparencia fiscal directiva DAC6 UE'
r = httpx.get('http://localhost:8001/v1/consulta', params={'q': q}, timeout=60.0)
print(f'Status: {r.status_code}')
print(f'Time: {r.elapsed.total_seconds():.1f}s')
data = r.json()
print(f'Modelos: {len(data.get("modelos", []))}')
for m in data.get('modelos', []):
    print(f'  {m["codigo"]}: {m.get("norma_base")}')
