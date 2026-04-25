import httpx, json, asyncio, time

async def test_subset():
    queries = [
        ("iva-001", "Tipo reducido IVA pan leche libros"),
        ("iva-002", "Autoliquidacion trimestral IVA modelo 303"),
        ("iva-003", "Entregas intracomunitarias de bienes modelo 349"),
        ("iva-006", "Como calcular la prorrata de deducciones en IVA"),
        ("irpf-001", "Declaracion anual IRPF modelo 100"),
        ("irpf-008", "Como deducirme la compra de casa vivienda habitual"),
        ("lgt-001", "Obligaciones formales tributarias LGT"),
        ("borme-001", "Publicacion junta general sociedades modificacion estatutos"),
        ("bdns-001", "Listado entidades credito supervision banco espana"),
        ("sem-001", "Cuanto pago de impuestos al comprar casa segunda mano"),
    ]
    
    start_total = time.time()
    async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=60.0, http2=False) as client:
        for i, (qid, q) in enumerate(queries, 1):
            start = time.time()
            try:
                r = await client.get("/v1/legislacion/buscar", params={"q": q}, timeout=60.0)
                elapsed = (time.time() - start) * 1000
                data = r.json()
                n = len(data.get("resultados", []))
                normas = [res.get("norma") for res in data.get("resultados", [])[:3]]
                print(f"[{i}/{len(queries)}] {qid}: {r.status_code} in {elapsed:.0f}ms, {n} resultados, normas={normas}")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                print(f"[{i}/{len(queries)}] {qid}: ERROR after {elapsed:.0f}ms - {e}")
    
    total = (time.time() - start_total) * 1000
    print(f"\nTotal: {total:.0f}ms ({total/1000:.1f}s)")

asyncio.run(test_subset())
