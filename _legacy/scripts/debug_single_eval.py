import urllib.request, json, re

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

# Test int-002 specifically
qid = "int-002"
q = "IRNR+rentas+sin+establecimiento+permanente"
fuente_esperada = ["IRNR"]

r = urllib.request.urlopen(f'http://localhost:8001/v1/consulta?q={q}')
d = json.loads(r.read())

# Replicate _extraer_fuentes exactly
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

print(f'Query: {qid} ({q})')
print(f'Fuentes encontradas raw: {fuentes}')

# Normalize
encontrados_norm = {SOURCE_ALIASES.get(f, f) for f in fuentes}
esperadas_norm = {SOURCE_ALIASES.get(f, f) for f in fuente_esperada}
print(f'Encontradas normalizadas: {encontrados_norm}')
print(f'Esperadas normalizadas: {esperadas_norm}')
print(f'Overlap: {encontrados_norm & esperadas_norm}')
print(f'ACIERTO FUENTE: {bool(encontrados_norm & esperadas_norm)}')

# Also check buscar endpoint
r2 = urllib.request.urlopen(f'http://localhost:8001/v1/legislacion/buscar?q={q}')
d2 = json.loads(r2.read())
buscar_fuentes = set()
for r3 in d2.get('resultados', []):
    if r3.get('norma'):
        buscar_fuentes.add(r3['norma'])
    if r3.get('fuente'):
        buscar_fuentes.add(r3['fuente'])
print(f'\nBuscar fuentes: {buscar_fuentes}')
print(f'Total combinadas: {fuentes | buscar_fuentes}')
