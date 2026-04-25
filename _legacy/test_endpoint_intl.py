import requests
import json

# Test FATCA
r = requests.get("http://localhost:8001/v1/consulta", params={"q": "FATCA", "limit": 5})
data = r.json()
print(f"FATCA - {len(data.get('resultados', []))} results")
for item in data.get('resultados', []):
    print(f"  {item.get('norma')}:{item.get('articulo')} - {item.get('texto')[:80]}...")

print()

# Test W-8BEN
r = requests.get("http://localhost:8001/v1/consulta", params={"q": "W-8BEN", "limit": 5})
data = r.json()
print(f"W-8BEN - {len(data.get('resultados', []))} results")
for item in data.get('resultados', []):
    print(f"  {item.get('norma')}:{item.get('articulo')} - {item.get('texto')[:80]}...")

print()

# Test CRS
r = requests.get("http://localhost:8001/v1/consulta", params={"q": "CRS intercambio automatico", "limit": 5})
data = r.json()
print(f"CRS - {len(data.get('resultados', []))} results")
for item in data.get('resultados', []):
    print(f"  {item.get('norma')}:{item.get('articulo')} - {item.get('texto')[:80]}...")
