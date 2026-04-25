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
data = tools_resp.json()
print(f"\n=== Tools list status: {tools_resp.status_code} ===")
if "result" in data:
    tools = data["result"].get("tools", [])
    print(f"Tools count: {len(tools)}")
    for t in tools[:5]:
        print(f"  - {t['name']}: {t.get('description', '')[:80]}")
    if len(tools) > 5:
        print(f"  ... and {len(tools) - 5} more")
else:
    print(f"Error: {data.get('error', {})}")
