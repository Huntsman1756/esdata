import httpx
import json

API = "http://localhost:8001"

queries = [
    ("Mecanismos transfronterizos DAC6", "int-005"),
    ("Comunicacion indicio blanqueo capitales modelo 19 SEPBLAC", "comp-001"),
    ("Informacion reservada CNMV mercados valores", "comp-002"),
    ("Transparencia fiscal directiva DAC6 UE", "comp-003"),
    ("Impuesto transmisiones patrimoniales ITPAJD", "mix-002"),
    ("Tasas locales hacendarias municipales", "mix-003"),
    ("Impuestos especiales hidrocarburos", "mix-004"),
]

for q, qid in queries:
    r = httpx.get(f"{API}/v1/consulta", params={"q": q}, timeout=10)
    data = r.json()
    modelos = data.get("modelos", [])
    resultados = data.get("resultados", [])
    normativa = data.get("normativa", [])
    obligacion = data.get("obligacion", [])
    print(f"\n=== {qid}: {q} ===")
    print(f"  modelos: {len(modelos)}, resultados: {len(resultados)}, normativa: {len(normativa)}, obligacion: {len(obligacion)}")
    for m in modelos[:3]:
        codigo = m.get("codigo", "?")
        nb = m.get("norma_base", "None")
        print(f"    modelo {codigo}: norma_base={nb}")
    for r_item in resultados[:2]:
        norma = r_item.get("norma", "None")
        articulo = r_item.get("articulo", "None")
        print(f"    resultado: norma={norma}, articulo={articulo}")
    for n in normativa[:2]:
        print(f"    normativa: {json.dumps(n, ensure_ascii=False)[:200]}")
    for o in obligacion[:2]:
        print(f"    obligacion: {json.dumps(o, ensure_ascii=False)[:200]}")
