# LangChain

## Objetivo

Consumir `esdata` desde `LangChain` como herramienta HTTP estructurada.

## Estado

`[PARTIAL]`

No hay paquete LangChain propio en el repo, pero la API y la spec OpenAPI permiten crear herramientas ligeras encima de `httpx` o del loader OpenAPI del framework.

## Patron recomendado

1. Crear un wrapper por endpoint de `esdata`.
2. Inyectar `X-API-Key` desde entorno del proceso LangChain.
3. Limitar las herramientas expuestas a lectura y retrieval.

## Ejemplo minimo

```python
import os
import httpx

BASE_URL = os.environ["ESDATA_API_BASE_URL"].rstrip("/")
API_KEY = os.environ["ESDATA_API_KEY"]


def buscar_legislacion(q: str) -> dict:
    response = httpx.get(
        f"{BASE_URL}/v1/legislacion/buscar",
        params={"q": q},
        headers={"X-API-Key": API_KEY},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()
```

## Prompt de sistema sugerido

```text
Eres un asistente especializado en fiscalidad y regulacion espanola. Usa las herramientas de esdata solo para recuperar evidencia. Responde con referencias exactas y abstente cuando no haya soporte suficiente.
```
