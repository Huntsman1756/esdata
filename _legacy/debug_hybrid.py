from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "apps" / "api"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)

r = client.get("/v1/legislacion/buscar/hybrid", params={"q": "IRPF modelo 100", "hybrid_weight": 0.5})
print(f"Status: {r.status_code}")
print(f"Body: {r.text[:2000]}")
