import asyncio, aiohttp, json, urllib.parse

QUERIES = [
    "Tipo reducido IVA pan leche libros",
    "Autoliquidacion IVA modelo 303",
    "Entregas intracomunitarias bienes modelo 349",
    "Tipo superreducido IVA alimentos",
    "IRPF modelo 100",
    "IRPF dividendos retencion modelo 124",
    "IRNR no residente modelo 216",
    "IRNR dividendos retencion modelo 124",
    "DAC6 mecanismos transfronterizos",
    "Comunicacion blanqueo capitales modelo 19 SEPBLAC",
]

WEIGHTS = [0.0, 0.3, 0.5, 0.7, 1.0]
BASE = "http://localhost:8001"

async def run_query(session, q, weight):
    url = f"{BASE}/v1/legislacion/buscar/hybrid?q={urllib.parse.quote(q)}&hybrid_weight={weight}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return len(data.get("resultados", [])), data
            return 0, None
    except Exception:
        return 0, None

async def main():
    async with aiohttp.ClientSession() as session:
        for w in WEIGHTS:
            print(f"\n=== hybrid_weight={w} ===")
            total = 0
            for q in QUERIES:
                n, data = await run_query(session, q, w)
                total += n
                sources = set()
                if data and "resultados" in data:
                    for r in data["resultados"]:
                        sources.update(r.get("rrf_sources", []))
                print(f"  q={q[:50]:50s} -> {n} results (sources: {sources})")
            print(f"  TOTAL: {total}/{len(QUERIES)*10}")

asyncio.run(main())
