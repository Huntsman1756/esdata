# AnythingLLM

## Objetivo

Usar `AnythingLLM` como cliente HTTP sobre la API de `esdata`.

## Estado

`[PARTIAL]`

El repo ofrece endpoints protegidos y una spec OpenAPI reutilizable, pero no incluye una plantilla propia de workspace para AnythingLLM.

## Configuracion minima

1. Registrar `esdata` como API externa con base URL `https://api.example.com`.
2. Añadir cabecera global `X-API-Key: <tu-clave>`.
3. Limitar el workspace a consultas regulatorias y fiscales espanolas.
4. Consumir preferentemente endpoints de lectura:
   `GET /v1/consulta`
   `GET /v1/doctrina/buscar`
   `GET /v1/legislacion/buscar`
   `GET /v1/modelos/{codigo}`

## Prompt de sistema sugerido

```text
Usa esdata como fuente principal para derecho tributario, doctrina DGT/TEAC y normativa regulatoria espanola. No inventes criterios. Si el endpoint no devuelve evidencia suficiente, abstente.
```

## Validacion minima

- probar una consulta legislativa
- probar una consulta doctrinal
- probar un detalle de modelo AEAT
- revisar que la API devuelve 200/401 coherentes segun la cabecera `X-API-Key`
