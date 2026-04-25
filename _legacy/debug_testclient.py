"""Debug: verify TestClient connects to PostgreSQL with seed data."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "apps" / "api"))

from pathlib import Path
import os
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://esdata:testpass@localhost:5434/esdata")

from fastapi.testclient import TestClient
from main import app
from db import DATABASE_URL

print(f"DATABASE_URL: {DATABASE_URL}")

client = TestClient(app, raise_server_exceptions=False)

# Test buscar endpoint
r = client.get("/v1/legislacion/buscar", params={"q": "IRPF modelo 100"})
print(f"\nBuscar status: {r.status_code}")
data = r.json()
results = data.get("resultados", [])
print(f"Resultados: {len(results)}")
for res in results[:5]:
    print(f"  norma={res.get('norma')} articulo={res.get('numero')} score={res.get('score')}")

# Test hybrid endpoint
r = client.get("/v1/legislacion/buscar/hybrid", params={"q": "IRPF modelo 100", "hybrid_weight": 0.5})
print(f"\nHybrid status: {r.status_code}")
data = r.json()
results = data.get("resultados", [])
print(f"Resultados: {len(results)}")
for res in results[:5]:
    print(f"  norma={res.get('norma')} articulo={res.get('numero')} score={res.get('score')}")

# Test IRPF queries from golden dataset
r = client.get("/v1/legislacion/buscar", params={"q": "obligacion presentar IRPF 12000 euros"})
print(f"\nIRPF 12000 status: {r.status_code}")
data = r.json()
results = data.get("resultados", [])
print(f"Resultados: {len(results)}")
for res in results[:5]:
    print(f"  norma={res.get('norma')} articulo={res.get('numero')} score={res.get('score')}")

# Test IVA queries
r = client.get("/v1/legislacion/buscar", params={"q": "tipo reducido IVA libros"})
print(f"\nIVA libros status: {r.status_code}")
data = r.json()
results = data.get("resultados", [])
print(f"Resultados: {len(results)}")
for res in results[:5]:
    print(f"  norma={res.get('norma')} articulo={res.get('numero')} score={res.get('score')}")
