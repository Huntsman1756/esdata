import httpx, json, sys
sys.path.insert(0, 'scripts')
from eval_phase3 import _extraer_fuentes

queries = [
    ('lgt-001', 'Obligaciones formales tributarias LGT'),
    ('irpf-008', 'Como deducirme la compra de casa vivienda habitual'),
    ('int-008', 'Contractor digital americano vendiendo a Espana'),
    ('comp-006', 'Registro contable de operaciones con terceros pais'),
    ('syn-003', 'Cuanto me descuentan del salario nomina'),
]

for qid, q in queries:
    try:
        r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': q}, timeout=30)
        buscar_resp = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
        fuentes_buscar = _extraer_fuentes(buscar_resp)
        
        r2 = httpx.get('http://localhost:8001/v1/consulta', params={'q': q}, timeout=30)
        consulta_resp = r2.json() if r2.headers.get('content-type', '').startswith('application/json') else {}
        fuentes_consulta = _extraer_fuentes(consulta_resp)
        
        all_fuentes = fuentes_buscar | fuentes_consulta
        print(f'{qid}: buscar={fuentes_buscar} consulta={fuentes_consulta} total={all_fuentes}')
    except Exception as e:
        print(f'{qid}: ERROR {e}')
