import json
with open('scripts/golden_queries.json') as f:
    data = json.load(f)
for q in data['queries']:
    if q['criterios'].get('articulo_esperado'):
        print(f"{q['id']}: {q['pregunta']}")
        print(f"  articulo_esperado: {q['criterios']['articulo_esperado']}")
        print(f"  fuente_esperada: {q['criterios']['fuente_esperada']}")
        print(f"  vigencia_necesaria: {q['criterios'].get('vigencia_necesaria')}")
        print(f"  chunk_esperado: {q['criterios'].get('chunk_esperado')}")
        print()
