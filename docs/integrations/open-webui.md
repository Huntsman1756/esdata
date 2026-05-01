# Open WebUI

## Objetivo

Conectar `Open WebUI` a `esdata` usando la API REST expuesta por FastAPI.

## Estado

`[PARTIAL]`

El repo ya tiene API protegida por `X-API-Key` y una spec OpenAPI reutilizable, pero no incluye un conector nativo ni una prueba end-to-end de Open WebUI.

## Configuracion minima

1. Exponer `esdata` por HTTPS o en red privada accesible desde Open WebUI.
2. Crear una credencial dedicada para `ESDATA_API_KEY`.
3. Usar como base URL la API de `esdata`, por ejemplo `https://api.example.com`.
4. Importar o referenciar la spec `docs/openapi-gpt.json` o `https://api.example.com/gpt-actions/modelos/openapi.json`.
5. Configurar cabecera fija: `X-API-Key: <tu-clave>`.

## Endpoints recomendados

- `GET /v1/legislacion/buscar`
- `GET /v1/legislacion/{codigo}/articulos/{numero}`
- `GET /v1/doctrina/buscar`
- `GET /v1/doctrina/{referencia}`
- `GET /v1/modelos`
- `GET /v1/modelos/{codigo}`

## Prompt de sistema sugerido

```text
Eres un asistente de fiscalidad y regulacion espanola. Responde solo con informacion recuperada de esdata. Cita siempre la fuente oficial o la referencia doctrinal exacta. Si la evidencia es insuficiente, di que no puedes concluir.
```

## Limites

- `Open WebUI` no consume `MCP` aqui; usa `REST/OpenAPI`.
- La validacion final depende de la version exacta de Open WebUI desplegada fuera del repo.
