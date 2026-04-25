import json

with open("scripts/eval_results/eval_20260425_165140.json") as f:
    data = json.load(f)

# Check iva-002
q = [x for x in data["results"] if x["query_id"] == "iva-002"][0]
print("=== iva-002 ===")
print("falla:", q["falla"])
print("score:", q["metricas"]["score_compuesto"])
print("acierto_fuente:", q["metricas"]["acierto_fuente"])
print("fuentes_esperadas:", q["metricas"]["fuentes_esperadas"])
print("fuentes_encontradas:", q["metricas"]["fuentes_encontradas"])

# Check buscar endpoint
buscar_data = q["endpoints"]["buscar"].get("data", {})
resultados = buscar_data.get("resultados", [])
print(f"\nbuscar resultados count: {len(resultados)}")
if resultados:
    print(f"Primera norma: {resultados[0].get('norma')}")
    print(f"Primera fuente: {resultados[0].get('fuente')}")

# Check hybrid endpoint
hybrid_data = q["endpoints"]["hybrid"].get("data", {})
hybr_resultados = hybrid_data.get("resultados", [])
print(f"\nhybrid resultados count: {len(hybr_resultados)}")
if hybr_resultados:
    print(f"Primera norma: {hybr_resultados[0].get('norma')}")
    print(f"Primera fuente: {hybr_resultados[0].get('fuente')}")

# Quick check a few more
print("\n=== Summary of failures ===")
for r in data["results"]:
    if r["falla"]:
        print(f"  {r['query_id']}: fuente={r['metricas']['acierto_fuente']} fuentes_encontradas={r['metricas']['fuentes_encontradas']} fuentes_esperadas={r['metricas']['fuentes_esperadas']}")
