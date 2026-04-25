import httpx, json

# Test exactly what evaluator sees for iva-003
q = "Entregas intracomunitarias de bienes modelo 349"
r = httpx.get("http://localhost:8001/v1/legislacion/buscar", params={"q": q}, timeout=10)
data = r.json()

print("=== buscar endpoint ===")
print(f"Status: {r.status_code}")
print(f"Resultados: {len(data.get('resultados', []))}")
for i, res in enumerate(data.get('resultados', [])[:3]):
    print(f"  [{i}] norma={res.get('norma')} numero={res.get('numero')}")

# Simulate _extraer_fuentes
fuentes = set()
for res in data.get("resultados", []):
    if res.get("norma"):
        fuentes.add(res["norma"])
    if res.get("fuente"):
        fuentes.add(res["fuente"])
print(f"Fuentes extraidas: {fuentes}")

# Also test consulta
r2 = httpx.get("http://localhost:8001/v1/consulta", params={"q": q}, timeout=10)
data2 = r2.json()
print(f"\n=== consulta endpoint ===")
print(f"Modelos: {len(data2.get('modelos', []))}")
for m in data2.get('modelos', [])[:3]:
    print(f"  modelo={m.get('codigo')} norma_base={m.get('norma_base')}")

# Simulate _extraer_fuentes for consulta
fuentes2 = set()
for m in data2.get("modelos", []):
    norma_base = m.get("norma_base", "")
    if norma_base:
        import re
        for match in re.finditer(r'[A-Z][A-Z0-9_]*', norma_base):
            token = match.group()
            if token in {"LIVA", "LIRPF", "LIRNR", "LIS", "LGT", "ITPAJD", "HL", "IIEE", "IRNR", "DAC6", "UE_INTRACOMUNITARIO", "SEPBLAC", "CNMV", "IMPCIB"}:
                fuentes2.add(token)
print(f"Fuentes consulta: {fuentes2}")
print(f"Union: {fuentes | fuentes2}")
