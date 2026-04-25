import httpx

queries = [
    ("iva-002", "Autoliquidacion trimestral IVA modelo 303"),
    ("iva-003", "Entregas intracomunitarias de bienes modelo 349"),
    ("iva-004", "Tipo superreducido IVA alimentos"),
    ("irpf-001", "Declaracion anual IRPF modelo 100"),
    ("lgt-001", "Obligaciones formales tributarias LGT"),
    ("comp-001", "Comunicacion indicio blanqueo capitales modelo 19 SEPBLAC"),
]

for qid, q in queries:
    r = httpx.get("http://localhost:8001/v1/legislacion/buscar", params={"q": q, "limit": 3}, timeout=10)
    data = r.json()
    resultados = data.get("resultados", [])
    normas = [res.get("norma") for res in resultados]
    print(f"{qid}: {len(resultados)} resultados, normas={normas[:3]}")
