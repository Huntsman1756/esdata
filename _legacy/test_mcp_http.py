import requests
import json
import uuid

BASE = "http://localhost:8001/mcp"
headers = {"Content-Type": "application/json", "Accept": "application/json"}

def call_mcp(method, params=None, msg_id=1, session_id=None):
    payload = {"jsonrpc": "2.0", "method": method, "id": msg_id}
    if params is not None:
        payload["params"] = params
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    r = requests.post(BASE, json=payload, headers=headers)
    return r.json(), r.headers

# Step 1: Initialize
r, hdrs = call_mcp("initialize", {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": {"name": "test", "version": "1.0"}
}, 1)
print("INIT:", json.dumps(r, indent=2)[:500])
session_id = hdrs.get("Mcp-Session-Id")
print(f"Session-ID: {session_id}")

# Step 2: List tools
r, _ = call_mcp("tools/list", msg_id=2, session_id=session_id)
print("\nTOOLS:", json.dumps(r, indent=2)[:500])

# Step 3: Call FATCA
r, _ = call_mcp("tools/call", {"name": "consulta_fiscal", "arguments": {"q": "FATCA reporting"}}, 3, session_id)
print("\nFATCA:")
result = r.get("result", {})
for c in result.get("content", []):
    text = c.get("text", "")
    print(f"  Text length: {len(text)}")
    print(text[:600])

# Step 4: Call CRS
r, _ = call_mcp("tools/call", {"name": "consulta_fiscal", "arguments": {"q": "CRS intercambio automatico"}}, 4, session_id)
print("\nCRS:")
result = r.get("result", {})
for c in result.get("content", []):
    text = c.get("text", "")
    print(f"  Text length: {len(text)}")
    print(text[:600])

# Step 5: Call W-8BEN
r, _ = call_mcp("tools/call", {"name": "consulta_fiscal", "arguments": {"q": "W-8BEN formulario"}}, 5, session_id)
print("\nW-8BEN:")
result = r.get("result", {})
for c in result.get("content", []):
    text = c.get("text", "")
    print(f"  Text length: {len(text)}")
    print(text[:600])
