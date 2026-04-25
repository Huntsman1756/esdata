#!/usr/bin/env python3
"""Evaluar subset de 20 queries del golden dataset."""
import httpx, json, asyncio, time

async def eval_subset():
    with open("scripts/golden_queries.json") as f:
        golden = json.load(f)
    
    # First 20 queries
    queries = golden["queries"][:20]
    
    start_total = time.time()
    async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=60.0, http2=False) as client:
        results = []
        for i, q in enumerate(queries, 1):
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
                
                # Simulate _extraer_fuentes
                fuentes = set()
                for res in resultados:
                    if res.get("norma"):
                        fuentes.add(res["norma"])
                
                match = bool(fuentes & set(fuentes_esperadas))
                status = "OK" if match else "FAIL"
                results.append({"id": qid, "match": match, "fuentes": fuentes, "esperadas": fuentes_esperadas})
                print(f"[{i}/{len(queries)}] {qid}: {status} in {elapsed:.0f}ms, fuentes={fuentes}")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                print(f"[{i}/{len(queries)}] {qid}: ERROR after {elapsed:.0f}ms - {e}")
    
    # Summary
    total = (time.time() - start_total) * 1000
    aciertos = sum(1 for r in results if r["match"])
    print(f"\n=== RESUMEN ({len(queries)} queries) ===")
    print(f"Aciertos: {aciertos}/{len(queries)} ({aciertos/len(queries)*100:.1f}%)")
    print(f"Tiempo total: {total/1000:.1f}s")
    
    # Save results
    with open("scripts/eval_results/subset_20.json", "w") as f:
        json.dump({"results": results, "total_ms": total}, f, indent=2)
    print("Guardado en scripts/eval_results/subset_20.json")

asyncio.run(eval_subset())
