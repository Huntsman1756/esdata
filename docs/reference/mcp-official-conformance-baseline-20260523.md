# MCP official conformance baseline - 2026-05-23

Estado: auditoria ejecutada contra VPS. No cambia runtime.

Commit auditado: `cb9651f8`.

## Objetivo

Medir el MCP HTTP productivo de ESData contra la suite oficial `@modelcontextprotocol/conformance` antes de seguir desarrollando mas funcionalidad.

Esta auditoria no intenta migrar `/mcp`, no cambia tools fiscales y no convierte el resultado en un gate obligatorio todavia. Sirve para separar:

- lo que el servidor MCP legacy ya cumple,
- lo que falla por features MCP no implementadas,
- lo que falla por diferencia entre servidor de producto y fixture generica de conformance,
- y lo que queda como deuda real de seguridad/transporte.

## Fuentes y herramienta usada

- Blog oficial MCP sobre la RC `2026-07-28`: <https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/>.
- Changelog draft oficial MCP: <https://modelcontextprotocol.io/specification/draft/changelog>.
- Suite oficial de conformance: `npx --yes @modelcontextprotocol/conformance`.

## Entorno de ejecucion

La suite oficial no expone una opcion de cabecera API en `server --help`. Como `/mcp` productivo exige `MCP_API_KEY`, se uso un proxy temporal en el VPS:

- escucha local: `http://127.0.0.1:8787/mcp`
- upstream: `http://127.0.0.1:8000/mcp`
- funcion: inyectar `X-API-Key` leyendo `/etc/esdata/esdata.env`
- alcance: solo auditoria; no deploy, no rebuild, no cambio de runtime

Comando base:

```bash
npx --yes @modelcontextprotocol/conformance server \
  --url http://127.0.0.1:8787/mcp
```

Se ejecuto primero la suite activa completa de una vez. Ese resultado quedo contaminado por `429 Too Many Requests` al disparar muchas pruebas en rafaga. Por eso el baseline valido es la repeticion secuencial con pausa entre escenarios.

## Resultado secuencial

Resumen:

- Escenarios ejecutados: `32`
- Escenarios pass: `7`
- Escenarios fail: `25`

Veredicto:

> ESData tiene un MCP legacy usable y parcialmente conforme para handshake, ping y tools basicas, pero no cumple el perfil optimo de conformance oficial MCP. No hay soporte completo de resources, prompts, completion, logging, progress, sampling, elicitation, fixtures multimedia/JSON Schema, ni hardening Host/Origin suficiente en la ruta de prueba localhost.

## Escenarios que pasan

| Escenario | Resultado | Lectura |
| --- | --- | --- |
| `server-initialize` | pass | El handshake legacy inicializa correctamente. |
| `ping` | pass | El metodo basico responde. |
| `tools-list` | pass | La lista de tools se expone correctamente para el flujo legacy. |
| `tools-call-simple-text` | pass | Una llamada simple de tool con texto funciona. |
| `tools-call-error` | pass | El servidor devuelve error MCP manejado cuando corresponde. |
| `server-sse-polling` | pass informativo | La prueba no ejecuta aserciones materiales en este entorno. |
| `server-sse-multiple-streams` | pass | El transporte SSE legacy soporta streams multiples segun la prueba. |

## Escenarios que fallan por features MCP no implementadas

| Escenario | Fallo observado | Interpretacion |
| --- | --- | --- |
| `logging-set-level` | `-32601 Method not found` | ESData no implementa logging MCP core. |
| `completion-complete` | `-32601 Method not found` | ESData no implementa completion MCP. |
| `resources-list` | `-32601 Method not found` | No hay superficie MCP resources. |
| `resources-read-text` | `-32601 Method not found` | No hay lectura de resources MCP. |
| `resources-read-binary` | `-32601 Method not found` | No hay resources binarios. |
| `resources-templates-read` | `-32601 Method not found` | No hay resource templates. |
| `resources-subscribe` | `-32601 Method not found` | No hay subscripcion resources. |
| `resources-unsubscribe` | `-32601 Method not found` | No hay baja de subscripcion resources. |
| `prompts-list` | `-32601 Method not found` | No hay superficie MCP prompts. |
| `prompts-get-simple` | `-32601 Method not found` | No hay prompts MCP. |
| `prompts-get-with-args` | `-32601 Method not found` | No hay prompts parametrizados. |
| `prompts-get-embedded-resource` | `-32601 Method not found` | No hay prompts con resources embebidos. |
| `prompts-get-with-image` | `-32601 Method not found` | No hay prompts con imagen. |

## Escenarios que fallan por fixtures esperadas por la suite

La suite oficial espera tools genericas de prueba. ESData expone tools de dominio fiscal/regulatorio, por lo que estos fallos no significan que las tools fiscales esten rotas, pero si impiden reclamar conformance optima oficial.

| Escenario | Fallo observado | Interpretacion |
| --- | --- | --- |
| `tools-call-image` | No se encontro contenido de imagen | No existe tool fixture `test_image_content`. |
| `tools-call-audio` | No se encontro contenido de audio | No existe tool fixture `test_audio_content`. |
| `tools-call-embedded-resource` | No se encontro resource embebido | No existe tool fixture de resource embebido. |
| `tools-call-mixed-content` | Falta contenido multiple imagen/resource | No existe tool fixture de contenido mixto. |
| `json-schema-2020-12` | Tool `json_schema_2020_12_tool` no encontrada | El catalogo no incluye fixture para preservar keywords JSON Schema 2020-12. |

## Escenarios que fallan por interaccion server-cliente no implementada

| Escenario | Fallo observado | Interpretacion |
| --- | --- | --- |
| `tools-call-with-logging` | `-32601 Method not found` | No hay flujo MCP logging desde tool. |
| `tools-call-with-progress` | No se recibieron notificaciones de progreso | No hay progress notifications MCP. |
| `tools-call-sampling` | El servidor no solicito sampling al cliente | No hay sampling MCP. |
| `tools-call-elicitation` | El servidor no solicito elicitation al cliente | No hay elicitation MCP. |
| `elicitation-sep1034-defaults` | El servidor no solicito elicitation | No hay soporte de defaults en elicitation. |
| `elicitation-sep1330-enums` | El servidor no solicito elicitation | No hay soporte de enums en elicitation. |

## Hallazgo de seguridad/transporte

| Escenario | Resultado | Lectura |
| --- | --- | --- |
| `dns-rebinding-protection` | fail parcial: `1/2` | La peticion localhost valida se acepta, pero una peticion con `Host`/`Origin` invalidos tambien recibio HTTP `200`. |

Este test se ejecuto contra un proxy temporal autenticado, no contra una exposicion publica sin API key. Aun asi, el resultado revela que la capa MCP/proxy local no rechaza `Host`/`Origin` invalidos. Debe tratarse como hardening pendiente si se quiere acercar el servidor al perfil oficial.

Seguimiento 2026-05-23: este hallazgo se separo como remediacion acotada de transporte. Tras desplegar el fix en VPS, la prueba oficial focal `dns-rebinding-protection` paso `2/2` via proxy local autenticado (`CONFORMANCE_DNS_STATUS=0`). El baseline completo original no se reescribe; cualquier mejora adicional debe validarse con una nueva ejecucion focal o un nuevo baseline completo.

## Relacion con MCP 2026-07-28

Este baseline mide el MCP legacy actual. No valida la RC `2026-07-28`.

La auditoria de compatibilidad `2026-07-28` sigue en `docs/reference/mcp-2026-07-28-compatibility-audit.md` y mantiene su conclusion:

- no sustituir `/mcp` en caliente,
- mantener legacy para clientes actuales,
- implementar fase B stateless en ruta/modo separado,
- validar requests autocontenidas sin `initialize` ni `Mcp-Session-Id`.

## Decision operativa

Estado honesto del proyecto:

> ESData no cumple aun los criterios optimos del MCP oficial. Cumple un subconjunto basico y util del transporte MCP legacy para tools de producto, pero la conformance oficial completa sigue siendo parcial.

## Siguientes acciones recomendadas

1. Mantener esta auditoria como baseline no bloqueante hasta decidir si se busca conformance oficial completa.
2. Crear un fichero de `expected-failures` si se quiere ejecutar la suite oficial en CI sin mezclar gaps conocidos con regresiones.
3. Mantener el hardening `Host`/`Origin` como gate de regresion; ya fue corregido y validado focalmente tras este baseline.
4. Decidir explicitamente si ESData debe implementar `resources`, `prompts`, `completion`, `logging`, `progress`, `sampling` y `elicitation`, o si quedan fuera de producto.
5. Si se persigue conformance oficial completa, anadir fixtures/tools de compatibilidad o adaptar el scope de la suite para no confundir herramientas fiscales con fixtures genericas.
6. Mantener la fase B `2026-07-28` como bloque separado de transporte stateless.

## No conclusiones

- No se detecto una regresion en las tools fiscales por este baseline.
- No se debe interpretar el resultado `7/32` como fallo de doctrina, AEAT, CDI o cobertura fiscal.
- No se debe vender el MCP como oficialmente optimo hasta pasar una suite de conformance acordada y actualizada.
