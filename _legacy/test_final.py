import sys, re
sys.path.insert(0, 'apps/api')
from services.search import _build_tsquery

queries = [
    "Autoliquidacion trimestral IVA modelo 303",
    "IRPF modelo 100 declaracion anual",
    "IRNR no residente rentas inmobiliarias modelo 216",
    "DAC6 mecanismos transfronterizos",
    "IVA resumen anual modelo 390",
]

for q in queries:
    print(f"Query: {q}")
    print(f"  tsquery: {_build_tsquery(q)}")
    print()
