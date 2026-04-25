import requests

s = requests.Session()

# Get session
sse_resp = s.get("http://localhost:8001/mcp", stream=True)
session_id = sse_resp.headers.get('mcp-session-id')
print(f"Session: {session_id}")

# Step 1: List tools
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}
headers = {"Content-Type": "application/json", "Accept": "application/json"}
if session_id:
    headers["MCP-Session-ID"] = session_id

tools_resp = s.post("http://localhost:8001/mcp", json=payload, headers=headers)
print(f"\n=== Tools list ===")
print(tools_resp.text[:500])

# Step 2: Call consulta_fiscal
payload2 = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "consulta_fiscal",
        "arguments": {
            "q": "residente eeuu facta"
        }
    }
}
tool_resp = s.post("http://localhost:8001/mcp", json=payload2, headers=headers)
print(f"\n=== Tool call ===")
print(tool_resp.text[:1000])
