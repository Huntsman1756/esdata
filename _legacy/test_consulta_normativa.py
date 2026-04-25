import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

s = requests.Session()

# Test: consulta fiscal con "entregas intracomunitarias" 
resp = s.get("http://localhost:8001/v1/consulta", params={"q": "entregas intracomunitarias"})
data = resp.json()
print("=== Consulta: entregas intracomunitarias ===")
print(f"Total resultados: {data.get('total_resultados', 0)}")
print(f"Modelos: {len(data.get('modelos', []))}")
for m in data.get('modelos', []):
    print(f"  - {m['codigo']}: {m['nombre']}")

print("\nResultados por tipo:")
normativa_count = 0
for r in data.get('resultados', []):
    print(f"  [{r['tipo']}] {r.get('codigo', r.get('norma', ''))}:{r.get('articulo', '')}")
    txt = r.get('texto', r.get('fragmento', ''))[:120]
    if txt:
        print(f"    {txt}...")
    if r['tipo'] == 'normativa':
        normativa_count += 1

print(f"\nNormativa encontrada: {normativa_count}")
