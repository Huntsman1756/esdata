from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
r = client.get("/v1/consulta", params={"q": "residente eeuu facta juridica"})
data = r.json()

for m in data["modelos"]:
    codigo = m["codigo"]
    nombre = m["nombre"]
    freq = m.get("frecuencia", "")
    oblig = m.get("obligados_resumen", "")
    print(f"{codigo} - {nombre} | {freq} | {oblig}")

print()
for m in data["modelos"]:
    for inst in m.get("instrucciones", []):
        if inst["seccion"] in ["quien-debe", "como-rellenar", "plazo"]:
            print(f"[{m['codigo']}] {inst['seccion']}: {inst['contenido'][:200]}")
