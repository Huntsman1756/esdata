import httpx
import re
import json

API = "http://localhost:8001"

def extraer_fuentes(resp):
    fuentes = set()
    for m in resp.get("modelos", []):
        norma_base = m.get("norma_base", "")
        if norma_base:
            for match in re.finditer(r'[A-Z][A-Z0-9]*', norma_base):
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
    
    print(f"\n=== {qid} ===")
    print(f"  fuentes encontradas: {fuentes}")
    print(f"  fuentes esperadas: {expected}")
    print(f"  acierto: {acierto}")
    print(f"  modelos count: {len(data.get('modelos', []))}")
    for m in data.get("modelos", []):
        print(f"    {m['codigo']}: norma_base={m.get('norma_base')}")
    
    # Calcular score manualmente
    acierto_fuente = acierto
    acierto_articulo = False  # simplificado
    acierto_vigencia = None
    chunk_precision = None
    recall_top3 = any(f in fuentes for f in expected)
    recall_top5 = any(f in fuentes for f in expected)
    acierto_doctrina = None
    acierto_modelo = None
    
    weights = {"fuente": 0.30, "articulo": 0.15, "vigencia": 0.10, "chunk": 0.10, "recall_top3": 0.15, "recall_top5": 0.10, "doctrina": 0.10, "modelo": 0.10}
    values = {
        "fuente": 1.0 if acierto_fuente else 0.0,
        "articulo": 1.0 if acierto_articulo else 0.0,
        "vigencia": 1.0 if acierto_vigencia else (0.0 if acierto_vigencia is not None else 1.0),
        "chunk": chunk_precision if chunk_precision is not None else 1.0,
        "recall_top3": 1.0 if recall_top3 else 0.0,
        "recall_top5": 1.0 if recall_top5 else 0.0,
        "doctrina": 1.0 if acierto_doctrina else (0.0 if acierto_doctrina is not None else 1.0),
        "modelo": 1.0 if acierto_modelo else (0.0 if acierto_modelo is not None else 1.0),
    }
    score = sum(weights[k] * values[k] for k in weights)
    print(f"  score calculado: {score:.3f}")
    print(f"  valores: {json.dumps(values, indent=4)}")
