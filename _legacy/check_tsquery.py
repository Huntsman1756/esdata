import sys
sys.path.insert(0, 'apps/api')
from services.search import _build_tsquery

# Probar el tsquery generado para las queries que fallan
queries = [
    "Autoliquidacion trimestral IVA modelo 303",
    "IRPF modelo 100 declaracion anual",
    "IRPF dividendos retencion modelo 124",
    "IRNR no residente rentas inmobiliarias modelo 216",
    "DAC6 mecanismos transfronterizos",
    "LGT procedimiento tributario",
    "IVA entreg intracomunitarias bienes modelo 349",
    "IVA resumen anual modelo 390",
    "IRPF ganancias patrimoniales",
    "Impuesto sociedades modelo IS",
]

for q in queries:
    tsq = _build_tsquery(q)
    print(f"Query: {q}")
    print(f"  tsquery: {tsq}")
    print()
