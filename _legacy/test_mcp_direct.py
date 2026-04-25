import json
import sys

# Simulate what mcp_stdio.py does: call consulta_fiscal via TestClient
sys.path.insert(0, r"G:\_Proyectos\esdata\apps\api")
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test 1: FATCA
print("=== TEST 1: FATCA ===")
r = client.get("/v1/consulta", params={"q": "FATCA reporting requirements"})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Total resultados: {data['total_resultados']}")
normas = set()
for item in data['resultados']:
    normas.add(item.get('norma', '?'))
print(f"Normas encontradas: {sorted(normas)}")
print()

# Test 2: CRS
print("=== TEST 2: CRS ===")
r = client.get("/v1/consulta", params={"q": "CRS intercambio automatico informacion"})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Total resultados: {data['total_resultados']}")
normas = set()
for item in data['resultados']:
    normas.add(item.get('norma', '?'))
print(f"Normas encontradas: {sorted(normas)[:15]}")
print()

# Test 3: W-8BEN
print("=== TEST 3: W-8BEN ===")
r = client.get("/v1/consulta", params={"q": "W-8BEN formulario certificado"})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Total resultados: {data['total_resultados']}")
normas = set()
for item in data['resultados']:
    normas.add(item.get('norma', '?'))
print(f"Normas encontradas: {sorted(normas)[:15]}")
print()

# Test 4: Convenio bilateral
print("=== TEST 4: Convenio Argentina ===")
r = client.get("/v1/consulta", params={"q": "convenio doble tributacion argentina"})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Total resultados: {data['total_resultados']}")
normas = set()
for item in data['resultados']:
    normas.add(item.get('norma', '?'))
print(f"Normas encontradas: {sorted(normas)[:15]}")
print()

# Test 5: DAC6
print("=== TEST 5: DAC6 ===")
r = client.get("/v1/consulta", params={"q": "DAC6 reporte mecanismos transfronterizos"})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Total resultados: {data['total_resultados']}")
normas = set()
for item in data['resultados']:
    normas.add(item.get('norma', '?'))
print(f"Normas encontradas: {sorted(normas)[:15]}")

# Test 6: GIIN
print("=== TEST 6: GIIN ===")
r = client.get("/v1/consulta", params={"q": "GIIN global intermediary identification"})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Total resultados: {data['total_resultados']}")
normas = set()
for item in data['resultados']:
    normas.add(item.get('norma', '?'))
print(f"Normas encontradas: {sorted(normas)[:15]}")

print()
print("=== ALL TESTS PASSED ===")
