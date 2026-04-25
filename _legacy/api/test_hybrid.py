import httpx
r = httpx.get("http://localhost:8000/v1/legislacion/buscar/hybrid", params={"q": "IVA", "limit": 5, "hybrid_weight": 0.5})
data = r.json()
if isinstance(data, list):
    for item in data[:5]:
        doc_id = item.get("doc_id")
        codigo = item.get("norma")
        fuente = item.get("fuente")
        score = item.get("score")
        tipo = item.get("tipo")
        print(f"  doc_id={doc_id} codigo={codigo} fuente={fuente} score={score} tipo={tipo}")
else:
    print(f"ERROR: {r.status_code} {r.text[:500]}")
