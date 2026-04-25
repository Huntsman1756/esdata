import json

with open("scripts/eval_results/eval_20260425_165140.json") as f:
    data = json.load(f)

# Check buscar endpoint status for failing queries
for qid in ["iva-003", "iva-004", "irpf-001", "lgt-001", "comp-001"]:
    q = [x for x in data["results"] if x["query_id"] == qid][0]
    buscar = q["endpoints"]["buscar"]
    hybrid = q["endpoints"]["hybrid"]
    consulta = q["endpoints"]["consulta"]
    print(f"{qid}:")
    print(f"  buscar: status={buscar.get('status')} lat={buscar.get('latencia_ms')}ms")
    print(f"  hybrid: status={hybrid.get('status')} lat={hybrid.get('latencia_ms')}ms")
    print(f"  consulta: status={consulta.get('status')} lat={consulta.get('latencia_ms')}ms")
    if buscar.get("status") == "ok":
        bd = buscar.get("data", {})
        print(f"  buscar resultados: {len(bd.get('resultados', []))}")
        if bd.get("resultados"):
            print(f"  primera norma: {bd['resultados'][0].get('norma')}")
    print()
