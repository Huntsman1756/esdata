import httpx, json, re, asyncio
from datetime import datetime, timezone

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

def _extraer_fuentes(resp: dict) -> set:
    fuentes = set()
    if "_error" in resp:
        return fuentes
    for m in resp.get("modelos", []):
        norma_base = m.get("norma_base", "")
        if norma_base:
            for match in re.finditer(r'[A-Z][A-Z0-9_]*', norma_base):
                token = match.group()
                if token in KNOWN_SOURCE_PREFIXES:
                    fuentes.add(token)
        codigo = m.get("codigo", "")
        if codigo and codigo in KNOWN_SOURCE_PREFIXES:
            fuentes.add(codigo)
    for r in resp.get("resultados", []):
        if r.get("norma"):
            fuentes.add(r["norma"])
        if r.get("fuente"):
            fuentes.add(r["fuente"])
    for n in resp.get("normativa", []):
        if n.get("norma"):
            fuentes.add(n["norma"])
    return fuentes

async def main():
    qid = "int-008"
    pregunta = "Contractor digital americano vendiendo a Espana"
    fuente_esperada = ["IRNR"]
    
    async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=30) as client:
        # consulta
        r = await client.get("/v1/consulta", params={"q": pregunta})
        consulta_resp = r.json()
        
        # buscar
        r = await client.get("/v1/legislacion/buscar", params={"q": pregunta, "norma": "LIRNR"})
        buscar_resp = r.json()
        
        # extraer fuentes como eval
        fuentes_buscar = _extraer_fuentes(buscar_resp)
        fuentes_consulta = _extraer_fuentes(consulta_resp)
        fuentes_encontradas = fuentes_buscar | fuentes_consulta
        
        encontrados_norm = {SOURCE_ALIASES.get(f, f) for f in fuentes_encontradas}
        esperadas_norm = {SOURCE_ALIASES.get(f, f) for f in fuente_esperada}
        acierto = bool(encontrados_norm & esperadas_norm)
        
        print(f'{qid}: "{pregunta}"')
        print(f'  Consulta resultados count: {len(consulta_resp.get("resultados", []))}')
        print(f'  Consulta modelos count: {len(consulta_resp.get("modelos", []))}')
        print(f'  Buscar resultados count: {len(buscar_resp.get("resultados", []))}')
        print(f'  Fuentes buscar: {fuentes_buscar}')
        print(f'  Fuentes consulta: {fuentes_consulta}')
        print(f'  Combinadas: {fuentes_encontradas}')
        print(f'  Encontradas norm: {encontrados_norm}')
        print(f'  Esperadas norm: {esperadas_norm}')
        print(f'  Overlap: {encontrados_norm & esperadas_norm}')
        print(f'  ACIERTO FUENTE: {acierto}')
        
        # Show consulta resultados types
        print('\n  Top 5 consulta resultados:')
        for r in consulta_resp.get('resultados', [])[:5]:
            print(f'    tipo={r.get("tipo")} norma={r.get("norma")} codigo={r.get("codigo")} rank={r.get("rank")}')
        
        # Show modelo norma_base
        print('\n  Top 5 modelos norma_base:')
        for m in consulta_resp.get('modelos', [])[:5]:
            print(f'    norma_base={m.get("norma_base")} codigo={m.get("codigo")}')

asyncio.run(main())
