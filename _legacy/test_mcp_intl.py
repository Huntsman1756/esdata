import subprocess
import json
import sys

def send_msg(proc, msg):
    payload = json.dumps(msg).encode('utf-8')
    header = f"Content-Length: {len(payload)}\r\n\r\n".encode('utf-8')
    proc.stdin.write(header + payload)
    proc.stdin.flush()
    # Read response
    header_line = proc.stdout.readline().decode('utf-8')
    if "Content-Length:" in header_line:
        cl = int(header_line.split(":")[1].strip())
        raw = proc.stdout.read(cl).decode('utf-8')
        return json.loads(raw)
    return None

proc = subprocess.Popen(
    [sys.executable, "mcp_stdio.py"],
    cwd=r"G:\_Proyectos\esdata\apps\api",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Initialize
init_msg = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {},
               "clientInfo": {"name": "test", "version": "1.0"}}
}
r = send_msg(proc, init_msg)
print("INIT:", json.dumps(r, indent=2)[:500])

# Notification initialized
notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
send_msg(proc, notif)

# List tools
list_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
r = send_msg(proc, list_msg)
tools = r.get("result", {}).get("tools", [])
print(f"\nTOOLS: {len(tools)} tools found")
for t in tools:
    print(f"  - {t['name']}")

# Call FATCA
call_msg = {
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "consulta_fiscal",
               "arguments": {"q": "FATCA reporting requirements"}}
}
r = send_msg(proc, call_msg)
result = r.get("result", {})
text = ""
for c in result.get("content", []):
    text += c.get("text", "")
print(f"\nFATCA result length: {len(text)} chars")
print(text[:800])

proc.terminate()
