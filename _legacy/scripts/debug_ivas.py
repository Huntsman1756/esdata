import json

with open("scripts/golden_queries.json", encoding="utf-8") as f:
    data = json.load(f)

ivas = [q for q in data["queries"] if q["dominio"] == "iva"]
print(f"Total IVA queries en golden: {len(ivas)}")
for q in ivas:
    print(f"  {q['id']}: {q['pregunta'][:60]} fuentes={q['criterios'].get('fuente_esperada')}")
