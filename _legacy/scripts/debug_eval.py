import httpx, json

q = "Autoliquidacion trimestral IVA modelo 303"
r = httpx.get("http://localhost:8001/v1/legislacion/buscar", params={"q": q, "limit": 5}, timeout=10)
data = r.json()
resultados = data.get("resultados", [])
print(f"Total resultados: {len(resultados)}")
for i, res in enumerate(resultados[:5]):
    print(f"  [{i}] norma={res.get('norma')} numero={res.get('numero')} tipo={res.get('tipo')}")

print("\n--- /v1/consulta ---")
r2 = httpx.get("http://localhost:8001/v1/consulta", params={"q": q}, timeout=10)
data2 = r2.json()
print(f"Modelos: {len(data2.get('modelos', []))}")
for m in data2.get("modelos", [])[:3]:
    print(f"  modelo={m.get('codigo')} norma_base={m.get('norma_base')}")
