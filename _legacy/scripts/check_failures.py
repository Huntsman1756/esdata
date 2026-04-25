import json

with open('scripts/eval_results/eval_20260425_154416.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for r in d.get('results', []):
    if r.get('falla'):
        fuentes_enc = r.get('fuentes_encontradas', [])
        fuentes_exp = r.get('fuentes_esperadas', [])
        print(f"{r['query_id']}: encontradas={fuentes_enc} esperadas={fuentes_exp} score={r.get('score_compuesto')}")
