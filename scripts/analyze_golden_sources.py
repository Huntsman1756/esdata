"""Analyze golden queries: compare expected sources vs actual API responses."""
import json
import urllib.parse
import urllib.request
import sys

BASE = "http://localhost:8001"

def fetch_json(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def get_buscar_normas(q):
    """Return list of (norma, tipo) from buscar endpoint."""
    result = fetch_json("/v1/legislacion/buscar", {"q": q})
    normas = []
    for r in result.get("resultados", []):
        normas.append({
            "norma": r.get("norma"),
            "numero": r.get("numero"),
            "tipo": r.get("tipo"),
            "fuente_norma": r.get("fuente_norma"),
        })
    return normas

def get_consulta_info(q):
    """Return modelos and normativa info from consulta endpoint."""
    result = fetch_json("/v1/consulta", {"q": q})
    modelos = []
    for m in result.get("modelos", []):
        modelos.append({
            "codigo": m.get("codigo"),
            "nombre": m.get("nombre"),
            "norma_base": m.get("norma_base"),
        })
    resultados = []
    for r in result.get("resultados", []):
        resultados.append({
            "tipo": r.get("tipo"),
            "norma": r.get("norma"),
            "codigo": r.get("codigo"),
            "fuente": r.get("fuente"),
            "articulo": r.get("articulo"),
        })
    return modelos, resultados

def main():
    with open("scripts/golden_queries.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data["queries"]
    print(f"Total queries: {len(queries)}")
    print("=" * 120)

    results = []
    for i, q in enumerate(queries):
        qid = q["id"]
        pregunta = q["pregunta"]
        dominio = q["dominio"]
        fuente_esperada = q["criterios"].get("fuente_esperada", [])
        modelo_esperado = q["criterios"].get("modelo_esperado")

        # Skip empty queries and edge cases
        if not pregunta or len(pregunta) <= 1:
            continue

        print(f"[{i+1}/{len(queries)}] {qid} (dominio={dominio})")
        print(f"  Query: {pregunta}")
        print(f"  Expected fuente: {fuente_esperada}")
        print(f"  Expected modelo: {modelo_esperado}")

        # Buscar endpoint
        buscar_normas = get_buscar_normas(pregunta)
        buscar_normas_set = set()
        for bn in buscar_normas:
            buscar_normas_set.add(bn["norma"])
            print(f"  Buscar: norma={bn['norma']} art={bn['numero']} tipo={bn['tipo']}")

        # Consulta endpoint
        consulta_modelos, consulta_resultados = get_consulta_info(pregunta)
        consulta_normas_set = set()
        consulta_modelos_set = set()
        for cm in consulta_modelos:
            consulta_modelos_set.add(cm["codigo"])
            print(f"  Consulta modelo: codigo={cm['codigo']} nombre={cm['nombre']} norma_base={cm['norma_base']}")
        for cr in consulta_resultados:
            if cr.get("norma"):
                consulta_normas_set.add(cr["norma"])
                print(f"  Consulta resultado: tipo={cr['tipo']} norma={cr['norma']} codigo={cr['codigo']} fuente={cr['fuente']}")

        results.append({
            "id": qid,
            "dominio": dominio,
            "pregunta": pregunta,
            "fuente_esperada": fuente_esperada,
            "modelo_esperado": modelo_esperado,
            "buscar_normas": buscar_normas,
            "buscar_normas_set": list(buscar_normas_set),
            "consulta_modelos": consulta_modelos,
            "consulta_modelos_set": list(consulta_modelos_set),
            "consulta_resultados": consulta_resultados,
            "consulta_normas_set": list(consulta_normas_set),
        })

        print()

    # Summary
    print("=" * 120)
    print("SUMMARY")
    print("=" * 120)

    for r in results:
        qid = r["id"]
        dominio = r["dominio"]
        pregunta = r["pregunta"]
        fuente_esperada = r["fuente_esperada"]
        buscar_normas = r["buscar_normas_set"]
        consulta_normas = r["consulta_normas_set"]
        consulta_modelos = r["consulta_modelos_set"]

        # Check if expected source is found
        all_actual = set(buscar_normas + consulta_normas)
        expected_found = False
        if fuente_esperada:
            for exp in fuente_esperada:
                if exp in all_actual:
                    expected_found = True
                    break

        status = "OK" if expected_found else "FAIL"

        print(f"\n[{status}] {qid} ({dominio})")
        print(f"  Query: {pregunta}")
        print(f"  Expected fuentes: {fuente_esperada}")
        print(f"  Actual buscar normas: {buscar_normas}")
        print(f"  Actual consulta normas: {consulta_normas}")
        print(f"  Actual consulta modelos: {consulta_modelos}")
        print(f"  All actual sources: {list(all_actual)}")

        # Suggest new expected source
        if not expected_found and all_actual:
            # Pick the most relevant source
            if "LIVA" in all_actual:
                suggested = "LIVA"
            elif "LIRPF" in all_actual:
                suggested = "LIRPF"
            elif "IRNR" in all_actual:
                suggested = "IRNR"
            elif "LGT" in all_actual:
                suggested = "LGT"
            elif "LIS" in all_actual:
                suggested = "LIS"
            elif "ITPAJD" in all_actual:
                suggested = "ITPAJD"
            elif "IIEE" in all_actual:
                suggested = "IIEE"
            elif "HL" in all_actual:
                suggested = "HL"
            else:
                suggested = all_actual.pop() if len(all_actual) == 1 else list(all_actual)
            print(f"  SUGGESTED new fuente_esperada: [{suggested}]")

    # Save detailed results for further processing
    with open("scripts/golden_analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n\nDetailed results saved to scripts/golden_analysis_results.json")

if __name__ == "__main__":
    main()
