# MCP 2026-07-28 compatibility audit

Estado: fase A, auditoria y contrato pendiente. No cambia runtime.

Fecha: 2026-05-23.

## Objetivo

Preparar ESData para MCP `2026-07-28` sin romper el transporte remoto actual basado en MCP `2025-03-26`.

Este documento no autoriza migrar `/mcp` en caliente. Define el estado real, la matriz de incompatibilidad, las pruebas pendientes y el plan de compatibilidad dual.

## Fuentes externas revisadas

- Blog oficial MCP, `The 2026-07-28 MCP Specification Release Candidate`, publicado el 2026-05-21: <https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/>.
- Changelog draft oficial MCP `Key Changes`, revision contra `2025-11-25`: <https://modelcontextprotocol.io/specification/draft/changelog>.
- Documentacion `fastapi-mcp` consultada via Context7: la libreria sigue documentando transporte HTTP MCP con gestion de sesion y compatibilidad OAuth/MCP `2025-03-26`.

## Estado actual ESData

| Superficie | Estado actual | Evidencia repo | Impacto 2026-07-28 |
| --- | --- | --- | --- |
| HTTP MCP remoto | Montado en `/mcp` con `FastApiMCP.mount_http` | `apps/api/mcp_server.py` | Mantener como legacy |
| Dependencia | `fastapi-mcp==0.4.0` | `apps/api/requirements.txt` | Verificar soporte nuevo antes de implementar transporte propio |
| Session manager | Se arranca en lifespan | `apps/api/main.py` | Incompatible con core stateless si se usa como requisito |
| Handshake HTTP | `GET /mcp` con `Accept: text/event-stream`, luego `initialize` | tests MCP y scripts de maintenance | No aplica a `2026-07-28` |
| Session id | `Mcp-Session-Id` / `MCP-Session-ID` requerido tras handshake | tests MCP y scripts de maintenance | Debe desaparecer en la via nueva |
| Version actual | `protocolVersion=2025-03-26` | `apps/api/mcp_stdio.py`, tests | Debe convivir con `2026-07-28`, no sustituirse sin rollout |
| Stdio MCP | Handshake `initialize`, `notifications/initialized`, `tools/list`, `tools/call` | `apps/api/mcp_stdio.py` | Requiere analisis separado; no mezclar con HTTP stateless |
| OpenCode docs | Documentan `/mcp` con `X-API-Key` y session behavior | `docs/integrations/opencode-local-and-vps.md`, `docs/operations/agent-notes.md` | Deben quedar marcadas como legacy hasta migracion |

## Cambios MCP 2026-07-28 que afectan al stack

| Cambio RC | Estado ESData | Decision |
| --- | --- | --- |
| Sin `initialize` / `notifications/initialized` | ESData lo usa en HTTP tests, stdio y scripts | No cambiar legacy; crear ruta/modo nuevo |
| Sin `Mcp-Session-Id` | ESData lo exige en flujos reales y validaciones | No usarlo en la via stateless |
| Requests autocontenidas | ESData depende de sesion de protocolo | Nueva ruta debe requerir `_meta` por request |
| Headers `MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name` | No existen en runtime actual | Anadir contract tests pendientes |
| `server/discover` obligatorio | No existe | Anadir contrato pendiente |
| `ttlMs` y `cacheScope` en resultados list/read | No existe | Anadir contrato pendiente para `tools/list` |
| Trace context en `_meta` | Auditoria propia existe, pero no mapea estas claves | Disenar propagacion a `query_audit_log`/observabilidad |
| Roots, Sampling y Logging deprecados | No hay soporte MCP core explicito localizado para roots/sampling/logging | No anadir soporte nuevo; usar OpenTelemetry/logging interno |
| Tasks extension | No aplica al runtime actual | Fuera de fase A |
| MCP Apps | No aplica al runtime actual | Fuera de fase A |

## Estrategia de compatibilidad dual

### Fase A: auditoria y contratos pendientes

Entregables:

- Este documento.
- Contract tests `xfail` para la futura via `2026-07-28`.
- Roadmap y notas operativas actualizadas.

No incluye runtime nuevo.

### Fase B: prototipo controlado

Abrir solo si `fastapi-mcp` no publica soporte compatible o si hay cliente real que lo necesite antes de julio.

Opciones:

1. Ruta paralela `/mcp/stateless`.
2. Negociacion estricta por `MCP-Protocol-Version` en `/mcp`, manteniendo compatibilidad legacy.

Preferencia inicial: `/mcp/stateless`, porque reduce el riesgo de romper clientes `2025-03-26` y permite pruebas aisladas.

## Contrato esperado para la via stateless

### `server/discover`

Debe aceptar request autocontenida sin sesion:

```http
POST /mcp/stateless
MCP-Protocol-Version: 2026-07-28
Mcp-Method: server/discover
Mcp-Name: server/discover
X-API-Key: <MCP_API_KEY>
Content-Type: application/json
```

Debe devolver identidad del servidor, versiones soportadas, capacidades y extensiones. No debe devolver `Mcp-Session-Id`.

### `tools/list`

Debe aceptar:

```http
POST /mcp/stateless
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/list
Mcp-Name: tools/list
X-API-Key: <MCP_API_KEY>
Content-Type: application/json
```

El body debe incluir `_meta` con:

- `io.modelcontextprotocol/protocolVersion`
- `io.modelcontextprotocol/clientInfo`
- `io.modelcontextprotocol/clientCapabilities`

La respuesta debe incluir:

- `tools`
- `ttlMs`
- `cacheScope`

### `tools/call`

Debe aceptar:

```http
POST /mcp/stateless
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: <tool-name>
X-API-Key: <MCP_API_KEY>
Content-Type: application/json
```

Reglas:

- `Mcp-Method` debe coincidir con `body.method`.
- `Mcp-Name` debe coincidir con `params.name` cuando `method=tools/call`.
- No se acepta `Mcp-Session-Id`.
- Si hay estado cross-call, debe ser un handle explicito en `params.arguments`, no sesion MCP.
- `traceparent`, `tracestate` y `baggage` en `_meta` deben propagarse a auditoria/observabilidad cuando exista implementacion.

## Tests pendientes

`apps/api/tests/test_mcp_20260728_contract.py` define tests `xfail(strict=True)` para:

- `server/discover` sin sesion.
- `tools/list` sin handshake y con `ttlMs/cacheScope`.
- `tools/call` autocontenida sin `Mcp-Session-Id`.
- rechazo por mismatch entre headers y body.
- rechazo por version ausente/no soportada.

Estos tests no deben convertirse en obligatorios hasta implementar fase B.

## No objetivos

- No migrar `/mcp` legacy.
- No borrar tests actuales de `2025-03-26`.
- No tocar tools fiscales, doctrina, AEAT o CDI.
- No implementar Tasks ni MCP Apps en esta fase.
- No asumir soporte de `fastapi-mcp` sin release/documentacion especifica.

## Criterio de salida fase A

- El estado legacy queda inventariado.
- La incompatibilidad con `2026-07-28` queda documentada.
- Existen tests pendientes que describen el contrato nuevo.
- La documentacion explica que `/mcp` sigue siendo legacy `2025-03-26`.
- No se rompe ningun cliente actual.

## Siguiente paso

Antes del 2026-07-28:

1. Revisar si `fastapi-mcp` publica soporte `2026-07-28`.
2. Si no hay soporte, prototipar `/mcp/stateless`.
3. Ejecutar tests pendientes sin `xfail`.
4. Validar con un cliente real antes de deprecar cualquier flujo legacy.
