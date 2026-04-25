import urllib.request, json

queries = [
    ("int-001", "No+residente+rentas+inmobiliarias+modelo+216"),
    ("int-002", "IRNR+rentas+sin+establecimiento+permanente"),
    ("int-003", "IRNR+dividendos+retencion+modelo+124"),
    ("int-004", "IRNR+ganancias+patrimoniales+no+residentes"),
    ("int-005", "Mecanismos+transfronterizos+DAC6"),
    ("int-006", "Operaciones+intracomunitarias+IVA+UE"),
    ("int-007", "Resumen+anual+retenciones+IRNR+modelo+296"),
    ("int-008", "Contractor+digital+americano+vendiendo+a+Espana"),
    ("int-009", "Prestador+de+servicios+frances+facturando+a+cliente+espanol"),
    ("mix-001", "Retencion+no+residente+EEUU+Alemania"),
]

KNOWN_SOURCE_PREFIXES = frozenset({
    "LIVA", "LIRPF", "LIRNR", "LIS", "LGT", "ITPAJD", "IRNR", "IIEE", "HL",
    "DAC6", "DAC6RD", "DAC6EU", "RIRPF", "RIVA", "RIS", "RD1080",
    "LIVA_IGIC", "SEPBLAC", "CNMV",
})

import re
for qid, q in queries:
    r = urllib.request.urlopen(f'http://localhost:8001/v1/consulta?q={q}')
    d = json.loads(r.read())
    
    # Extract sources like _extraer_fuentes does
    fuentes = set()
    for m in d.get('modelos', []):
        norma_base = m.get('norma_base', '')
        if norma_base:
            for match in re.finditer(r'[A-Z][A-Z0-9_]*', norma_base):
                token = match.group()
                if token in KNOWN_SOURCE_PREFIXES:
                    fuentes.add(token)
        codigo = m.get('codigo', '')
        if codigo and codigo in KNOWN_SOURCE_PREFIXES:
            fuentes.add(codigo)
    
    for r2 in d.get('resultados', []):
        if r2.get('norma'):
            fuentes.add(r2['norma'])
        if r2.get('fuente'):
            fuentes.add(r2['fuente'])
    
    for n in d.get('normativa', []):
        if n.get('norma'):
            fuentes.add(n['norma'])
    
    print(f'{qid}: fuentes={fuentes}')
