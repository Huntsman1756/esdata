import httpx, time

start = time.time()
r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': 'IRNR'}, timeout=30)
elapsed = time.time() - start
print(f'Response time: {elapsed:.2f}s')
print(f'Status: {r.status_code}')
data = r.json()
print(f'Total: {data.get("total", 0)}')
print(f'Results: {len(data.get("resultados", []))}')
