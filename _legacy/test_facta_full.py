import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

s = requests.Session()

# Test 1: consulta fiscal con FactA keywords
resp = s.get("http://localhost:8001/v1/consulta", params={"q": "no residente facta modelo 216"})
data = resp.json()
print("=== Consulta: no residente facta modelo 216 ===")
print(f"Total resultados: {data.get('total_resultados', 0)}")
print(f"Modelos: {len(data.get('modelos', []))}")
for m in data.get('modelos', []):
    print(f"  - {m['codigo']}: {m['nombre']}")
    for i in m.get('instrucciones', []):
        print(f"    [{i['seccion']}] {i['titulo'][:60]}")

print("\nResultados:")
for r in data.get('resultados', []):
    print(f"  [{r['tipo']}] {r.get('codigo', r.get('norma', ''))}:{r.get('articulo', '')}")
    txt = r.get('texto', r.get('fragmento', ''))[:100]
    if txt:
        print(f"    {txt}...")

# Test 2: full-text search con "entregas intracomunitarias"
print("\n=== Buscar: entregas intracomunitarias ===")
resp2 = s.get("http://localhost:8001/v1/buscar", params={"q": "entregas intracomunitarias", "norma": "LIVA"})
data2 = resp2.json()
print(f"Resultados: {len(data2.get('resultados', []))}")
for r in data2.get('resultados', [])[:5]:
    txt = r.get('texto', '')[:120]
    if txt:
        print(f"  [{r.get('norma', '')}] {txt}...")

# Test 3: consulta con IRNR keywords
print("\n=== Consulta: IRNR dividendos no residente ===")
resp3 = s.get("http://localhost:8001/v1/consulta", params={"q": "IRNR dividendos no residente"})
data3 = resp3.json()
print(f"Total: {data3.get('total_resultados', 0)}")
print(f"Modelos: {len(data3.get('modelos', []))}")
for m in data3.get('modelos', []):
    print(f"  - {m['codigo']}: {m['nombre']}")
for r in data3.get('resultados', [])[:5]:
    print(f"  [{r['tipo']}] {r.get('norma', r.get('codigo', ''))}:{r.get('articulo', '')}")
    txt = r.get('texto', r.get('fragmento', ''))[:100]
    if txt:
        print(f"    {txt}...")
