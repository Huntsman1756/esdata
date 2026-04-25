import requests
s = requests.Session()

# Step 1: Connect via SSE
sse_resp = s.get("http://localhost:8001/mcp", stream=True)
session_id = sse_resp.headers.get('mcp-session-id')
print(f"Session ID: {session_id}")

# Step 2: List tools
headers = {"Content-Type": "application/json", "Accept": "application/json"}
if session_id:
    headers["MCP-Session-ID"] = session_id

tools_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}
tools_resp = s.post("http://localhost:8001/mcp", json=tools_payload, headers=headers)
print(f"\nTools list status: {tools_resp.status_code}")
tools_data = tools_resp.json()
print(f"Has result: {'result' in tools_data}")
if 'error' in tools_data:
    print(f"Error: {tools_data['error']}")
else:
    tools = tools_data.get("result", {}).get("tools", [])
    print(f"Tools: {[t['name'] for t in tools]}")

# Step 3: Call tool - try different formats
print("\n=== Trying format 1: params.arguments ===")
call1 = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "consulta_fiscal",
        "arguments": {"q": "no residente facta"}
    }
}
r1 = s.post("http://localhost:8001/mcp", json=call1, headers=headers)
print(f"Status: {r1.status_code}")
print(f"Body: {r1.text[:500]}")

print("\n=== Trying format 2: params with name only ===")
call2 = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "consulta_fiscal"
    }
}
r2 = s.post("http://localhost:8001/mcp", json=call2, headers=headers)
print(f"Status: {r2.status_code}")
print(f"Body: {r2.text[:500]}")
