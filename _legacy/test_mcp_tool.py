import requests

# Test MCP tool via HTTP endpoint
# MCP tools are called via POST to /mcp with JSON-RPC

# First do the SSE handshake
s = requests.Session()

# Step 1: Get session ID from headers
s = requests.Session()
sse_resp = s.get("http://localhost:8001/mcp", stream=True)
session_id = sse_resp.headers.get('mcp-session-id')

if not session_id:
    print("No session ID found")
    print("Headers:", dict(sse_resp.headers))
else:
    print(f"Session: {session_id}")
    
    # Step 2: Call the tool
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "consulta_fiscal",
            "arguments": {
                "q": "residente eeuu facta modelo 216"
            }
        }
    }
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if session_id:
        headers["MCP-Session-ID"] = session_id
    
    tool_resp = s.post("http://localhost:8001/mcp", json=payload, headers=headers)
    print(f"\nTool call status: {tool_resp.status_code}")
    print(f"Tool response: {tool_resp.text[:500]}")
