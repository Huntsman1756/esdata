import httpx
import json

API = "http://localhost:8001"

queries = [
    ("Mecanismos transfronterizos DAC6", "int-005"),
    ("Transparencia fiscal directiva DAC6 UE", "comp-003"),
]

for q, qid in queries:
    r = httpx.get(f"{API}/v1/consulta", params={"q": q}, timeout=10)
    data = r.json()
    print(f"\n=== {qid}: {q} ===")
    print("modelos:", json.dumps(data.get("modelos", []), ensure_ascii=False, indent=2)[:1000])
    print("resultados:", json.dumps(data.get("resultados", []), ensure_ascii=False, indent=2)[:1000])
