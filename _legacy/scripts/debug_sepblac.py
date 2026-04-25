import httpx

q = "Comunicacion indicio blanqueo capitales modelo 19 SEPBLAC"
r = httpx.get("http://localhost:8001/v1/consulta", params={"q": q}, timeout=10)
data = r.json()
print(f"modelos: {len(data.get('modelos', []))}")
for m in data.get('modelos', [])[:5]:
    print(f"  modelo={m.get('codigo')} norma_base={m.get('norma_base')}")
print(f"normativa: {len(data.get('normativa', []))}")
for n in data.get('normativa', [])[:5]:
    print(f"  norma={n.get('norma')} articulo={n.get('articulo')}")
