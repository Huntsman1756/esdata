import httpx
import re
import json

API = "http://localhost:8001"

def extraer_fuentes(resp):
    fuentes = set()
    for m in resp.get("modelos", []):
        norma_base = m.get("norma_base", "")
        if norma_base:
            for match in re.finditer(r'[A-Z]+', norma_base):
                fuentes.add(match.group())
    for r in resp.get("resultados", []):
        if r.get("norma"):
            fuentes.add(r["norma"])
    return fuentes

queries = [
    ("Mecanismos transfronterizos DAC6", "int-005", ["DAC6", "DAC6RD"]),
    ("Transparencia fiscal directiva DAC6 UE", "comp-003", ["DAC6", "DAC6EU"]),
]

for q, qid, expected in queries:
    r = httpx.get(f"{API}/v1/consulta", params={"q": q}, timeout=10)
    data = r.json()
    fuentes = extraer_fuentes(data)
    acierto = any(f in fuentes for f in expected)
    print(f"\n=== {qid}: {q} ===")
    print(f"  fuentes encontradas: {fuentes}")
    print(f"  fuentes esperadas: {expected}")
    print(f"  acierto_fuente: {acierto}")
    print(f"  modelos count: {len(data.get('modelos', []))}")
    for m in data.get("modelos", []):
        print(f"    modelo {m['codigo']}: norma_base={m.get('norma_base')}")
