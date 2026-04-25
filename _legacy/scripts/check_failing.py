import httpx, json

queries = [
    ('lgt-001', 'Obligaciones formales tributarias LGT'),
    ('lgt-002', 'Prescripcion deudas tributarias LGT'),
    ('lgt-003', 'Procedimiento tributarioLGTRG'),
    ('lgt-004', 'Repercuusion tipos impositivos LGT'),
    ('lgt-005', 'Liquidacion tributaria comprobacion valores LGT'),
    ('lgt-006', 'Subsidios solidaridad LGT'),
    ('lgt-007', 'Responsables tributarios LGT'),
    ('irpf-008', 'Como deducirme la compra de casa vivienda habitual'),
    ('irpf-009', 'Que impuestos paga una SL al constituirse'),
    ('int-008', 'Contractor digital americano vendiendo a Espana'),
    ('comp-006', 'Registro contable de operaciones con terceros pais'),
    ('syn-003', 'Cuanto me descuentan del salario nomina'),
]

for qid, q in queries:
    try:
        r = httpx.get('http://localhost:8001/v1/legislacion/buscar', params={'q': q}, timeout=30)
        d = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
        resultados = d.get('resultados', [])
        
        print(f'=== {qid} ===')
        print(f'  Total resultados: {len(resultados)}')
        for res in resultados[:5]:
            norma = res.get('norma', 'N/A')
            fuente = res.get('fuente', 'N/A')
            titulo = res.get('titulo', '')[:80]
            print(f'  - norma={norma} fuente={fuente} titulo={titulo}')
        print()
    except Exception as e:
        print(f'{qid}: ERROR {e}')
