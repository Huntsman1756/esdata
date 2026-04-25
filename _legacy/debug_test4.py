import sys
sys.path.insert(0, '/app')

from services.search import search_legislacion

# Test the actual search function
result = search_legislacion('IRNR rentas sin establecimiento permanente')
print('Result keys:', result.keys())
print('Query:', result.get('q'))
print('Results count:', len(result.get('resultados', [])))
for r in result.get('resultados', [])[:5]:
    print('  ', r.get('norma'), 'art.', r.get('numero'), r.get('fragmento', '')[:80])
