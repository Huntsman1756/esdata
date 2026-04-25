import httpx, asyncio

queries = {
    "iva-002": "Autoliquidacion trimestral IVA modelo 303",
    "iva-003": "Entregas intracomunitarias de bienes modelo 349",
    "iva-004": "Tipo superreducido IVA alimentos",
    "irpf-001": "Declaracion anual IRPF modelo 100",
    "lgt-001": "Obligaciones formales tributarias LGT",
    "comp-001": "Comunicacion indicio blanqueo capitales modelo 19 SEPBLAC",
}

async def test_query(qid, q):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get("http://localhost:8001/v1/legislacion/buscar", params={"q": q}, timeout=30.0)
            data = r.json()
            resultados = data.get("resultados", [])
            normas = [res.get("norma") for res in resultados[:3]]
            return f"OK: {len(resultados)} resultados, normas={normas}"
    except Exception as e:
        return f"ERROR: {e}"

async def main():
    for qid, q in queries.items():
        result = await test_query(qid, q)
        print(f"{qid}: {result}")

asyncio.run(main())
