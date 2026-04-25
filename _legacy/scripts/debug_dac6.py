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
    for r_item in data.get("resultados", []):
        t = r_item.get("tipo", "?")
        n = r_item.get("norma", "?")
        a = r_item.get("articulo", "?")
        txt = str(r_item.get("texto", ""))[:150]
        print(f"  {t}: norma={n} articulo={a} texto={txt}")
    for m in data.get("modelos", []):
        print(f"  modelo {m.get('codigo')}: norma_base={m.get('norma_base')}")
