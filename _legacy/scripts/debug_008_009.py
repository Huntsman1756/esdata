import urllib.request, json, re
from urllib.parse import quote

KNOWN_SOURCE_PREFIXES = frozenset({
    "LIVA", "LIRPF", "LIRNR", "LIS", "LGT", "ITPAJD", "IRNR", "IIEE", "HL",
    "DAC6", "DAC6RD", "DAC6EU", "RIRPF", "RIVA", "RIS", "RD1080",
    "LIVA_IGIC", "SEPBLAC", "CNMV",
})

SOURCE_ALIASES = {
    "LIRPF": "IRPF", "LIRNR": "IRNR", "LIVA": "IVA",
    "LIS": "IS", "LGT": "LGT", "ITPAJD": "ITPAJD",
    "RIRPF": "IRPF", "RIVA": "IVA", "RIS": "IS",
}

queries = [
    ("int-008", "Contractor digital americano vendiendo a Espana", ["IRNR"]),
    ("int-009", "Prestador de servicios frances facturando a cliente espanol", ["LIVA", "DAC6"]),
]

for qid, pregunta, fuente_esperada in queries:
    q = quote(pregunta)
    
    # /v1/legislacion/buscar
    r1 = urllib.request.urlopen(f'http://localhost:8001/v1/legislacion/buscar?q={q}')
    d1 = json.loads(r1.read())
    
    # /v1/consulta
    r2 = urllib.request.urlopen(f'http://localhost:8001/v1/consulta?q={q}')
    d2 = json.loads(r2.read())
    
    # Extract sources like eval does
    fuentes_buscar = set()
    for r in d1.get('resultados', []):
        if r.get('norma'):
            fuentes_buscar.add(r['norma'])
        if r.get('fuente'):
            fuentes_buscar.add(r['fuente'])
    
    fuentes_consulta = set()
    for m in d2.get('modelos', []):
        norma_base = m.get('norma_base', '')
        if norma_base:
            for match in re.finditer(r'[A-Z][A-Z0-9_]*', norma_base):
                token = match.group()
                if token in KNOWN_SOURCE_PREFIXES:
                    fuentes_consulta.add(token)
        codigo = m.get('codigo', '')
        if codigo and codigo in KNOWN_SOURCE_PREFIXES:
            fuentes_consulta.add(codigo)
    for r in d2.get('resultados', []):
        if r.get('norma'):
            fuentes_consulta.add(r['norma'])
        if r.get('fuente'):
            fuentes_consulta.add(r['fuente'])
    for n in d2.get('normativa', []):
        if n.get('norma'):
            fuentes_consulta.add(n['norma'])
    
    fuentes_encontradas = fuentes_buscar | fuentes_consulta
    encontrados_norm = {SOURCE_ALIASES.get(f, f) for f in fuentes_encontradas}
    esperadas_norm = {SOURCE_ALIASES.get(f, f) for f in fuente_esperada}
    acierto = bool(encontrados_norm & esperadas_norm)
    
    print(f'{qid}: "{pregunta}"')
    print(f'  Buscar fuentes: {fuentes_buscar}')
    print(f'  Buscar resultados count: {len(d1.get("resultados", []))}')
    print(f'  Consulta fuentes: {fuentes_consulta}')
    print(f'  Consulta resultados count: {len(d2.get("resultados", []))}')
    print(f'  Combinadas: {fuentes_encontradas}')
    print(f'  Encontradas norm: {encontrados_norm}')
    print(f'  Esperadas norm: {esperadas_norm}')
    print(f'  Overlap: {encontrados_norm & esperadas_norm}')
    print(f'  ACIERTO FUENTE: {acierto}')
    print()
