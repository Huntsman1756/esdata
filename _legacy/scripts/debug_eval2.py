import httpx, json

# Test iva-002
q = "Autoliquidacion trimestral IVA modelo 303"
r = httpx.get("http://localhost:8001/v1/legislacion/buscar", params={"q": q, "limit": 10}, timeout=10)
data = r.json()

# Simular _extraer_fuentes
fuentes = set()
for res in data.get("resultados", []):
    if res.get("norma"):
        fuentes.add(res["norma"])
    if res.get("fuente"):
        fuentes.add(res["fuente"])

print(f"Fuentes encontradas: {fuentes}")
print(f"Fuentes esperadas: ['LIVA']")
print(f"Match: {'LIVA' in fuentes}")

# Check what the evaluator actually sees - check the response structure
print(f"\nResponse keys: {list(data.keys())}")
print(f"First result keys: {list(data.get('resultados', [{}])[0].keys())}")
print(f"First result: {json.dumps(data['resultados'][0], indent=2, ensure_ascii=False)[:500]}")
