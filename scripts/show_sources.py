import json
with open('scripts/golden_queries.json') as f:
    data = json.load(f)
for q in data['queries']:
    fuentes = q['criterios'].get('fuente_esperada', [])
    print(f"{q['id']:15} dom={q['dominio']:15} fuentes={fuentes}")
