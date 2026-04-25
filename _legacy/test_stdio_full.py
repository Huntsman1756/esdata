import subprocess, json, sys

# Initialize
init = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
}

def send_msg(proc, msg):
    json_str = json.dumps(msg)
    payload = json_str.encode('utf-8')
    header = f"Content-Length: {len(payload)}\r\n\r\n".encode()
    proc.stdin.write(header + payload)
    proc.stdin.flush()

def read_msg(proc):
    line = proc.stdout.readline().decode().strip()
    if not line:
        return None
    if "Content-Length:" in line:
        cl = int(line.split(":")[1].strip())
        body = proc.stdout.read(cl).decode()
        return json.loads(body)
    return json.loads(line)

# Start stdio server
proc = subprocess.Popen(
    [sys.executable, "mcp_stdio.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd="G:\\_Proyectos\\esdata\\apps\\api"
)

# Send initialize
send_msg(proc, init)
resp = read_msg(proc)
print(f"Initialize: {resp.get('result', {}).get('protocolVersion')}")

# Send initialized notification
send_msg(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

# Read any notification response (none expected)
try:
    resp = read_msg(proc)
except:
    pass

# List tools
send_msg(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
resp = read_msg(proc)
tools = resp.get("result", {}).get("tools", [])
print(f"\nTools count: {len(tools)}")
for t in tools:
    print(f"  - {t['name']}")

# Call consulta_fiscal
send_msg(proc, {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "consulta_fiscal",
        "arguments": {"q": "residente eeuu facta modelo 216"}
    }
})
resp = read_msg(proc)
if "error" in resp:
    print(f"\nError: {resp['error']}")
else:
    content = resp.get("result", {}).get("content", [{}])[0]
    text = content.get("text", "")
    print(f"\n=== Tool call response ===")
    print(f"Length: {len(text)} chars")
    print(text[:800])

proc.terminate()
