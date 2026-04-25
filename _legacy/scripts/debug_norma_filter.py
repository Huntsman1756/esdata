import urllib.request, json
from urllib.parse import quote

# int-008 sin filtro norma
q = quote('Contractor digital americano vendiendo a Espana')
r1 = urllib.request.urlopen('http://localhost:8001/v1/legislacion/buscar?q=' + q)
d1 = json.loads(r1.read())
print('=== int-008 SIN filtro norma ===')
print('Resultados:', len(d1.get('resultados', [])))
for x in d1.get('resultados', [])[:5]:
    print('  norma=%s fuente=%s fuente_norma=%s' % (x.get('norma'), x.get('fuente'), x.get('fuente_norma')))

# int-008 CON filtro norma=LIRNR
r2 = urllib.request.urlopen('http://localhost:8001/v1/legislacion/buscar?q=' + q + '&norma=LIRNR')
d2 = json.loads(r2.read())
print()
print('=== int-008 CON filtro norma=LIRNR ===')
print('Resultados:', len(d2.get('resultados', [])))
for x in d2.get('resultados', [])[:5]:
    print('  norma=%s fuente=%s fuente_norma=%s' % (x.get('norma'), x.get('fuente'), x.get('fuente_norma')))

# int-009 sin filtro norma
q2 = quote('Prestador de servicios frances facturando a cliente espanol')
r3 = urllib.request.urlopen('http://localhost:8001/v1/legislacion/buscar?q=' + q2)
d3 = json.loads(r3.read())
print()
print('=== int-009 SIN filtro norma ===')
print('Resultados:', len(d3.get('resultados', [])))
for x in d3.get('resultados', [])[:5]:
    print('  norma=%s fuente=%s fuente_norma=%s' % (x.get('norma'), x.get('fuente'), x.get('fuente_norma')))

# int-009 CON filtro norma=LIRNR (if present)
r4 = urllib.request.urlopen('http://localhost:8001/v1/legislacion/buscar?q=' + q2 + '&norma=LIRNR')
d4 = json.loads(r4.read())
print()
print('=== int-009 CON filtro norma=LIRNR ===')
print('Resultados:', len(d4.get('resultados', [])))
for x in d4.get('resultados', [])[:5]:
    print('  norma=%s fuente=%s fuente_norma=%s' % (x.get('norma'), x.get('fuente'), x.get('fuente_norma')))
