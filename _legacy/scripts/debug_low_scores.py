import httpx
import json

API = "http://localhost:8001"

# Queries con score bajo
queries = [
    ("Tipo reducido IVA pan leche libros", "iva-001", 0.500),
    ("Tipo superreducido IVA alimentos", "iva-004", 0.500),
    ("No residente rentas inmobiliarias modelo 216", "int-001", 0.500),
    ("Rentas sin establecimiento permanente IRNR", "int-002", 0.650),
    ("IRNR dividendos retencion modelo 124", "int-003", 0.650),
    ("IRNR ganancias patrimoniales no residentes", "int-004", 0.500),
    ("Mecanismos transfronterizos DAC6", "int-005", 0.750),
    ("Impuesto transmisiones patrimoniales ITPAJD", "mix-002", 0.750),
    ("Impuestos especiales hidrocarburos", "mix-004", 0.750),
]

for q, qid, expected_score in queries:
    r = httpx.get(f"{API}/v1/consulta", params={"q": q}, timeout=10)
    data = r.json()
    normativas = [x for x in data.get("resultados", []) if x.get("tipo") == "normativa"]
    modelos = data.get("modelos", [])
    
    print(f"\n=== {qid}: {q} (expected score={expected_score}) ===")
    print(f"  modelos: {len(modelos)}")
    for m in modelos:
        print(f"    {m['codigo']}: norma_base={m.get('norma_base')}")
    print(f"  normativas: {len(normativas)}")
    for n in normativas[:3]:
        print(f"    norma={n.get('norma')} articulo={n.get('articulo')} texto={str(n.get('texto',''))[:100]}")
    
    # Also check buscar endpoint
    r2 = httpx.get(f"{API}/v1/legislacion/buscar", params={"q": q}, timeout=10)
    if r2.status_code == 200:
        buscar = r2.json()
        buscar_results = buscar.get("resultados", [])
        print(f"  buscar results: {len(buscar_results)}")
        for br in buscar_results[:3]:
            print(f"    norma={br.get('norma')} articulo={br.get('articulo')} score={br.get('score')}")
    else:
        print(f"  buscar ERROR: {r2.status_code}")
