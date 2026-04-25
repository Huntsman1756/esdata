import httpx, json, asyncio

async def main():
    pregunta = "Contractor digital americano vendiendo a Espana"
    async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=30) as client:
        r = await client.get("/v1/consulta", params={"q": pregunta})
        d = r.json()
        print("Keys:", list(d.keys()))
        print("modelos count:", len(d.get("modelos", [])))
        print("resultados count:", len(d.get("resultados", [])))
        print("total_resultados:", d.get("total_resultados"))
        if d.get("resultados"):
            print("\nFirst resultado keys:", list(d["resultados"][0].keys()))
            print("First resultado:", json.dumps(d["resultados"][0], indent=2, ensure_ascii=False)[:500])
        if d.get("modelos"):
            print("\nFirst modelo keys:", list(d["modelos"][0].keys()))
            print("First modelo:", json.dumps(d["modelos"][0], indent=2, ensure_ascii=False)[:500])

asyncio.run(main())
