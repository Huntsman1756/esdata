# Diseno - Fase 6.1 alineacion documental de superficies MCP

## Objetivo

Alinear la documentacion activa con el comportamiento real del runtime para que un lector distinga sin ambiguedad entre `REST/OpenAPI`, `HTTP MCP` y `stdio MCP`, sin cambiar codigo ni ampliar el scope a tests nuevos.

## Problema confirmado

- `docs/manual-usuario/06-api-y-ejemplos.md` mezcla hoy ejemplos y framing de `API` HTTP con `/mcp`, lo que hace facil interpretar `HTTP MCP` como si fuera un endpoint REST mas.
- `docs/manual-usuario/07-mcp-y-clientes.md` ya reconoce dos superficies MCP, pero todavia necesita reforzar mejor que `HTTP MCP` y `stdio MCP` no comparten catalogo ni se integran igual.
- `docs/integrations/opencode-local-and-vps.md` esta orientado a `OpenCode` sobre `/mcp`, pero el boundary con `stdio` debe quedar aun mas explicito para evitar extrapolaciones de tools no soportadas por URL.
- `docs/architecture.md` describe bien `HTTP MCP` y `stdio MCP`, pero debe dejar mas explicita la tercera superficie de integracion estable del sistema: `REST/OpenAPI`.
- El runtime ya confirma esa separacion:
  - `apps/api/mcp_server.py` monta `/mcp` con `include_operations=HTTP_MCP_OPERATIONS`.
  - `apps/api/mcp_catalog.py` mantiene por separado `HTTP_MCP_OPERATIONS` y `get_stdio_tool_definitions()`.
  - `apps/api/mcp_stdio.py` expone tools de mas alto nivel que no deben asumirse presentes en `HTTP MCP`.

## Decision

- `docs/manual-usuario/06-api-y-ejemplos.md` pasara a ser un capitulo de `REST/OpenAPI` solamente.
- `docs/manual-usuario/07-mcp-y-clientes.md` sera la fuente funcional para `MCP`, con separacion explicita entre `HTTP MCP` y `stdio MCP`.
- `docs/integrations/opencode-local-and-vps.md` quedara limitada a `OpenCode` consumiendo `HTTP MCP` por URL, con una exclusion explicita de `stdio`.
- `docs/architecture.md` describira tres superficies distintas y complementarias:
  - `REST/OpenAPI`
  - `HTTP MCP`
  - `stdio MCP`
- `Fase 6.1` no anade tests de contrato nuevos ni cambia comportamiento del runtime; solo corrige documentacion viva y roadmap.

## Alcance aprobado

Incluye:

- actualizar `docs/architecture.md` para reflejar la separacion factual entre las tres superficies
- quitar de `docs/manual-usuario/06-api-y-ejemplos.md` el framing de `/mcp` como si perteneciera al mismo capitulo operativo que REST/OpenAPI
- reforzar en `docs/manual-usuario/07-mcp-y-clientes.md` la diferencia entre catalogo HTTP y catalogo stdio, incluyendo casos de uso recomendados
- dejar `docs/integrations/opencode-local-and-vps.md` explicitamente acotado a `OpenCode -> HTTP MCP`
- actualizar `docs/master-execution-roadmap.md` para reclamar, cerrar y dejar `6.2` como siguiente paso exacto cuando el slice termine

No incluye:

- cambios en `apps/api/`
- anadir o editar tests de `6.2`
- ampliar el barrido a docs fuera de los cuatro archivos objetivo y el roadmap
- cambiar contratos de auth, deploy o entorno ya fijados en fases anteriores

## Cambios previstos por archivo

### `docs/architecture.md`

- mantener el tono arquitectonico y factual
- explicitar que `REST/OpenAPI` es la superficie mas estable para integraciones backend/app tradicionales
- mantener `HTTP MCP` y `stdio MCP` como superficies separadas, sin tratarlas como un catalogo comun
- evitar convertir esta doc en una guia de uso paso a paso

### `docs/manual-usuario/06-api-y-ejemplos.md`

- eliminar `/mcp` de las secciones que presenten las superficies del capitulo como API REST
- mantener ejemplos y recomendaciones centrados en endpoints REST/OpenAPI
- dejar un puntero corto a `07-mcp-y-clientes.md` para cualquier integracion MCP
- corregir cualquier ejemplo operativo que se haya quedado con framing MCP mezclado dentro del capitulo

### `docs/manual-usuario/07-mcp-y-clientes.md`

- presentar primero la regla base: `HTTP MCP` y `stdio MCP` son dos superficies distintas
- explicar que `HTTP MCP` usa `/mcp` y solo expone el catalogo `HTTP_MCP_OPERATIONS`
- explicar que `stdio MCP` vive en `apps/api/mcp_stdio.py` y expone tools de mas alto nivel no equivalentes a HTTP
- mantener detalles utiles de seguridad, auditoria y uso interno, pero con wording orientado a evitar falsas equivalencias

### `docs/integrations/opencode-local-and-vps.md`

- mantener el documento como guia de `OpenCode` contra `HTTP MCP`
- hacer mas visible la regla `OpenCode via URL -> HTTP MCP`, `stdio` fuera de scope
- mantener ejemplos de handshake y configuracion solo para la ruta HTTP y `MCP_API_KEY`

### `docs/master-execution-roadmap.md`

- dejar `6.1` reclamado mientras dure el slice
- al cierre, registrar evidencia documental/verificacion y dejar `6.2` como siguiente paso exacto

## Verificacion prevista

- lectura final de los cuatro docs tocados y del resumen vivo del roadmap
- comprobacion de rutas y referencias entre `06`, `07` y la guia de `OpenCode`
- grep puntual para confirmar:
  - que `06-api-y-ejemplos.md` ya no ensena `/mcp` como parte del capitulo REST
  - que `07-mcp-y-clientes.md` no vende `HTTP MCP` y `stdio MCP` como catalogo unico
  - que `opencode-local-and-vps.md` sigue explicitamente acotado a `HTTP MCP`

## Aceptacion

- un lector puede distinguir sin ambiguedad cuando usar `REST/OpenAPI`, cuando usar `HTTP MCP` y cuando hablar de `stdio MCP`
- `docs/manual-usuario/06-api-y-ejemplos.md` queda como capitulo REST/OpenAPI-only
- `docs/manual-usuario/07-mcp-y-clientes.md` deja explicito que `HTTP MCP` y `stdio MCP` no comparten catalogo ni transporte
- `docs/integrations/opencode-local-and-vps.md` deja claro que `OpenCode` via URL consume solo `HTTP MCP`
- `docs/architecture.md` documenta la separacion como hecho arquitectonico estable
- el roadmap queda listo para cerrar `6.1` y apuntar a `6.2`
