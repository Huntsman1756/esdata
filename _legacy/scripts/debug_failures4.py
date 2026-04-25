import httpx
import json

API = "http://localhost:8001"

queries = [
    ("Impuesto transmisiones patrimoniales ITPAJD", "mix-002"),
    ("Tasas locales hacendarias municipales", "mix-003"),
    ("Impuestos especiales hidrocarburos", "mix-004"),
    ("Comunicacion indicio blanqueo capitales modelo 19 SEPBLAC", "comp-001"),
]

for q, qid in queries:
    r = httpx.get(f"{API}/v1/consulta", params={"q": q}, timeout=10)
    data = r.json()
    print(f"\n=== {qid}: {q} ===")
    resultados = data.get("resultados", [])
    for i, res in enumerate(resultados[:3]):
        print(f"  result[{i}]: {json.dumps(res, ensure_ascii=False, indent=4)[:500]}")
