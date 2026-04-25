import json

with open("scripts/eval_results/eval_20260425_165140.json") as f:
    data = json.load(f)

# Check error for iva-003
qid = "iva-003"
q = [x for x in data["results"] if x["query_id"] == qid][0]
buscar = q["endpoints"]["buscar"].get("data", {})
print(f"buscar error: {buscar.get('_error', 'no error key')}")
print(f"buscar keys: {list(buscar.keys())}")
print(f"buscar content[:500]: {json.dumps(buscar, ensure_ascii=False)[:500]}")

# Check iva-002 which passed
qid2 = "iva-002"
q2 = [x for x in data["results"] if x["query_id"] == qid2][0]
buscar2 = q2["endpoints"]["buscar"].get("data", {})
print(f"\niva-002 buscar status: {q2['endpoints']['buscar'].get('status')}")
print(f"iva-002 buscar _error: {buscar2.get('_error', 'no error key')}")
