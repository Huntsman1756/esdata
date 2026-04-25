import httpx
import re

API = "http://localhost:8001"

# Simular el extract_keywords
KEYWORD_MODELOS = {
    "dac6": ["DAC6"],
    "planificación agresiva": ["DAC6"],
    "mecanismos transfronterizos": ["DAC6"],
    "transparencia fiscal": ["DAC6"],
    "directiva dac6": ["DAC6"],
    "ue": ["216", "349", "124"],
    "unión europea": ["216", "349", "124"],
    "europa": ["216", "349", "124"],
    "eu": ["216", "349", "124"],
}

queries = [
    "Mecanismos transfronterizos DAC6",
    "Transparencia fiscal directiva DAC6 UE",
]

for q in queries:
    q_lower = q.lower()
    keywords = []
    sorted_kw = sorted(KEYWORD_MODELOS.keys(), key=len, reverse=True)
    for kw in sorted_kw:
        if kw in q_lower:
            keywords.append(kw)
    
    priority = []
    seen = set()
    for kw in keywords:
        for code in KEYWORD_MODELOS.get(kw, []):
            if code not in seen:
                priority.append(code)
                seen.add(code)
    
    print(f"\nQuery: {q}")
    print(f"  Keywords detectadas: {keywords}")
    print(f"  Modelos resueltos: {priority}")
