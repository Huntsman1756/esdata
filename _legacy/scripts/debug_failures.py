import httpx
import json

API = "http://localhost:8001"

queries = [
    "rentas inmobiliarias no residente modelo 216",
    "rentas sin establecimiento permanente IRNR",
    "IRNR dividendos retencion modelo 124",
    "IRNR ganancias patrimoniales no residentes",
    "Mecanismos transfronterizos DAC6",
    "Retencion no residente EEUU Alemania",
    "Impuesto transmisiones patrimoniales ITPAJD",
    "Tasas locales hacendarias municipales",
    "Impuestos especiales hidrocarburos",
    "Retenciones ingresos a cuenta modelo 111",
    "Retenciones arrendamientos urbanos modelo 115",
]

for q in queries:
    r = httpx.get(f"{API}/v1/consulta", params={"q": q}, timeout=10)
    data = r.json()
    modelos = data.get("modelos", [])
    resultados = data.get("resultados", [])
    normativa = data.get("normativa", [])
    print(f"\n=== {q} ===")
    print(f"  modelos: {len(modelos)}, resultados: {len(resultados)}, normativa: {len(normativa)}")
    for m in modelos[:3]:
        codigo = m.get("codigo", "?")
        nb = m.get("norma_base", "None")
        print(f"    modelo {codigo}: norma_base={nb}")
    for r_item in resultados[:2]:
        norma = r_item.get("norma", "None")
        articulo = r_item.get("articulo", "None")
        print(f"    resultado: norma={norma}, articulo={articulo}")
