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

def extraer_articulos(resp):
    articulos = []
    import re
    for r in resp.get("resultados", []):
        if r.get("articulo"):
            articulos.append(str(r["articulo"]))
        if r.get("numero"):
            articulos.append(str(r["numero"]))
    for m in resp.get("modelos", []):
        norma_base = m.get("norma_base", "")
        if norma_base:
            match = re.search(r'art\.\s*(\d+)', norma_base, re.IGNORECASE)
            if match:
                articulos.append(match.group(1))
    for n in resp.get("normativa", []):
        if n.get("articulo"):
            articulos.append(str(n["articulo"]))
        if n.get("numero"):
            articulos.append(str(n["numero"]))
    return articulos

def get_all_items(resp):
    items = []
    items.extend(resp.get("resultados", []))
    items.extend(resp.get("normativa", []))
    items.extend(resp.get("modelos", []))
    items.extend(resp.get("obligacion", []))
    return items

queries = [
    ("Tipo reducido IVA pan leche libros", "iva-001"),
    ("Tipo superreducido IVA alimentos", "iva-004"),
]

for q, qid in queries:
    r = httpx.get(f"{API}/v1/consulta", params={"q": q}, timeout=10)
    data = r.json()
    
    fuentes = extraer_fuentes(data)
    articulos = extraer_articulos(data)
    items = get_all_items(data)
    
    print(f"\n=== {qid}: {q} ===")
    print(f"  fuentes: {fuentes}")
    print(f"  articulos: {articulos}")
    print(f"  items totales: {len(items)}")
    
    for i, item in enumerate(items[:5]):
        norma = item.get("norma", "") or item.get("codigo", "")
        print(f"  item[{i}]: tipo={item.get('tipo')} norma/codigo={norma}")
