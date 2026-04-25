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
    print(f"\n=== {qid} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
