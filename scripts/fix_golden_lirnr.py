import json
with open('scripts/golden_queries.json', encoding='utf-8') as f:
    data = json.load(f)

count = 0
for q in data['queries']:
    fuentes = q.get('criterios', {}).get('fuente_esperada', [])
    if 'LIRNR' in fuentes:
        fuentes[fuentes.index('LIRNR')] = 'IRNR'
        count += 1
        print(f"  {q['id']}: {q['pregunta'][:60]}")

print(f'Total queries corregidas: {count}')
with open('scripts/golden_queries.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
