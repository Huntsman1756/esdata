import requests
r = requests.get('http://localhost:8000/v1/legislacion/buscar', params={'q': 'Autoliquidacion trimestral IVA modelo 303'})
import json
print(json.dumps(r.json(), indent=2, ensure_ascii=False))
