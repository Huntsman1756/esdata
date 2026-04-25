import httpx, json, asyncio, time

async def test_10():
    # Load golden queries and pick first 10
    with open("scripts/golden_queries.json") as f:
        golden = json.load(f)
    
    queries_to_test = golden["queries"][:10]
    
    start_total = time.time()
    async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=60.0, http2=False) as client:
        for i, q in enumerate(queries_to_test, 1):
            qid = q["id"]
            pregunta = q["pregunta"]
            criterios = q["criterios"]
            fuentes_esperadas = criterios.get("fuente_esperada", [])
            
            start = time.time()
            try:
                r = await client.get("/v1/legislacion/buscar", params={"q": pregunta}, timeout=60.0)
                elapsed = (time.time() - start) * 1000
                data = r.json()
                resultados = data.get("resultados", [])
                normas = [res.get("norma") for res in resultados[:3]]
                
                # Simulate _extraer_fuentes
                fuentes = set()
                for res in resultados:
                    if res.get("norma"):
                        fuentes.add(res["norma"])
                
                match = bool(fuentes & set(fuentes_esperadas))
                status = "OK" if match else "FAIL"
                print(f"[{i}/{len(queries_to_test)}] {qid}: {status} in {elapsed:.0f}ms, fuentes={fuentes}, esperadas={fuentes_esperadas}")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                print(f"[{i}/{len(queries_to_test)}] {qid}: ERROR after {elapsed:.0f}ms - {e}")
    
    total = (time.time() - start_total) * 1000
    print(f"\nTotal: {total:.0f}ms ({total/1000:.1f}s)")

asyncio.run(test_10())
