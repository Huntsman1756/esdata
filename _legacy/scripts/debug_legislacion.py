import httpx
import json

API = "http://localhost:8001"

# Test legislacion buscar endpoint
r = httpx.get(f"{API}/v1/legislacion/buscar", params={"q": "transmisiones patrimoniales", "norma": "ITPAJD"}, timeout=10)
print(f"legislacion/buscar ITPAJD: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  resultados: {len(data.get('resultados', []))}")
    for item in data.get("resultados", [])[:3]:
        print(f"    norma={item.get('norma')}, articulo={item.get('articulo')}")

# Test legislacion endpoint directo
r = httpx.get(f"{API}/v1/legislacion/buscar", params={"q": "tasas locales", "norma": "HL"}, timeout=10)
print(f"\nlegislacion/buscar HL: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  resultados: {len(data.get('resultados', []))}")
    for item in data.get("resultados", [])[:3]:
        print(f"    norma={item.get('norma')}, articulo={item.get('articulo')}")

# Test legislacion directo por norma
r = httpx.get(f"{API}/v1/legislacion/buscar", params={"q": "hidrocarburos", "norma": "IIEE"}, timeout=10)
print(f"\nlegislacion/buscar IIEE: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  resultados: {len(data.get('resultados', []))}")
    for item in data.get("resultados", [])[:3]:
        print(f"    norma={item.get('norma')}, articulo={item.get('articulo')}")

# Test consulta directa para SEPBLAC
r = httpx.get(f"{API}/v1/consulta", params={"q": "blanqueo capitales SEPBLAC"}, timeout=10)
print(f"\nconsulta blanqueo SEPBLAC: {r.status_code}")
data = r.json()
modelos = data.get("modelos", [])
obligacion = data.get("obligacion", [])
print(f"  modelos: {len(modelos)}, obligacion: {len(obligacion)}")
for m in modelos[:3]:
    print(f"    modelo {m.get('codigo')}: norma_base={m.get('norma_base')}")
for o in obligacion[:2]:
    print(f"    obligacion: {o.get('codigo')}")
