import httpx, re

KNOWN_SOURCE_PREFIXES = frozenset({
    "LIVA", "LIRPF", "LIRNR", "LIS", "LGT", "ITPAJD", "IRNR", "IIEE", "HL",
    "DAC6", "DAC6RD", "DAC6EU", "RIRPF", "RIVA", "RIS", "RD1080",
    "LIVA_IGIC", "SEPBLAC", "CNMV", "UE_INTRACOMUNITARIO", "IMPCIB",
    "ES_DE_CONVENIO", "ES_US_CONVENIO", "ES_FR_CONVENIO", "PT_ES_CONVENIO",
})

# Test consulta endpoint for comp-001
q = "Comunicacion indicio blanqueo capitales modelo 19 SEPBLAC"
r = httpx.get("http://localhost:8001/v1/consulta", params={"q": q}, timeout=10)
data = r.json()

fuentes = set()
for m in data.get("modelos", []):
    norma_base = m.get("norma_base", "")
    if norma_base:
        for match in re.finditer(r'[A-Z][A-Z0-9_]*', norma_base):
            token = match.group()
            if token in KNOWN_SOURCE_PREFIXES:
                fuentes.add(token)
    codigo = m.get("codigo", "")
    if codigo and codigo in KNOWN_SOURCE_PREFIXES:
        fuentes.add(codigo)

print(f"Fuentes consulta: {fuentes}")
print(f"SEPBLAC found: {'SEPBLAC' in fuentes}")
