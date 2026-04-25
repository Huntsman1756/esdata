import requests

# Test search via MCP endpoint
# First, the MCP SSE handshake
s = requests.Session()

# Test 1: search endpoint
resp = s.get("http://localhost:8001/v1/buscar", params={
    "q": "entregas intracomunitarias no residente",
    "norma": "LIVA"
})
print("=== Buscar: entregas intracomunitarias no residente (LIVA) ===")
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Resultados: {len(data.get('resultados', []))}")
for r in data.get("resultados", [])[:3]:
    print(f"  - {r.get('titulo', '')[:80]}")
    print(f"    Norma: {r.get('norma', '')}, Art: {r.get('articulo', '')}")
    txt = r.get('texto', '')[:150]
    print(f"    Texto: {txt}...")
    print()

# Test 2: consultar endpoint
resp2 = s.get("http://localhost:8001/v1/consulta", params={
    "q": "residente eeuu facta modelo 216"
})
print("=== Consulta: residente eeuu facta modelo 216 ===")
print(f"Status: {resp2.status_code}")
data2 = resp2.json()
import sys
sys.stdout.reconfigure(encoding='utf-8')
print(f"Modelos: {data2.get('modelos', [])}")
for m in data2.get("modelos", []):
    print(f"  - Modelo {m.get('codigo', '')}: {m.get('nombre', '')[:60]}")
    instr = m.get("instrucciones", [])
    for i in instr[:2]:
        print(f"      {i.get('seccion', '')}: {i.get('contenido', '')[:100]}...")

# Test 3: buscar legislación con keywords FactA
resp3 = s.get("http://localhost:8001/v1/buscar", params={
    "q": "W-8BEN FATCA residencia fiscal"
})
print("\n=== Buscar: W-8BEN FATCA residencia fiscal ===")
print(f"Status: {resp3.status_code}")
data3 = resp3.json()
print(f"Resultados: {len(data3.get('resultados', []))}")
for r in data3.get("resultados", [])[:3]:
    print(f"  - {r.get('titulo', '')[:80]}")
    print(f"    Norma: {r.get('norma', '')}")
    txt = r.get('texto', '')[:150]
    print(f"    Texto: {txt}...")
