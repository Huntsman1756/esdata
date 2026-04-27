# MCP y clientes

## Que es MCP en esdata

`esdata` expone una superficie `MCP` para clientes compatibles con Model Context Protocol.

En el estado actual del repo existen dos formas principales:

- MCP HTTP montado en `/mcp`
- MCP `stdio` implementado en `apps/api/mcp_stdio.py`

## MCP HTTP

La API monta MCP HTTP sobre FastAPI en la ruta:

```text
/mcp
```

La proteccion del endpoint incluye:

- guard especifico para `/mcp`
- soporte de API key por cabecera `X-API-Key`
- rate limiting especifico para esa ruta
- trazabilidad mediante `X-Request-ID` en las operaciones internas que ejecuta el catalogo MCP

Estado operativo actual:

- si `MCP_API_KEY` tiene valor, `/mcp` exige `X-API-Key`
- fuera de `APP_ENV=test`, el runtime no debe arrancar sin `MCP_API_KEY`
- el rate limit se controla con `MCP_RATE_LIMIT_PER_MINUTE`
- las herramientas MCP que terminan en `consulta_fiscal` heredan disclaimer IA, score de grounding y abstencion cuando no hay evidencia suficiente
- en tests de transporte HTTP, `MCP` debe montarse sobre una instancia fresca creada con `create_app()`; reutilizar la `app` global entre event loops puede dejar el session manager interno en estado invalido

Ejemplo de llamada HTTP con API key:

```bash
curl -s http://127.0.0.1:8000/mcp -H "X-API-Key: secret"
```

## MCP stdio

El servidor `stdio` usa JSON-RPC sobre `stdin/stdout` con cabeceras `Content-Length`.

Esto esta pensado para clientes locales o integraciones que prefieren un proceso hijo en lugar de exponer un endpoint HTTP.

Archivo relevante:

```text
apps/api/mcp_stdio.py
```

## Herramientas MCP relevantes hoy

Catalogo compartido actual:

- `consulta_fiscal`
- `listar_obligaciones_operativas`
- `listar_obligaciones_aplicables`
- `listar_deadlines`
- `get_obligacion_completa`
- `agente_consulta`
- `agente_monitoreo_status`
- `agente_compliance_resumen`

## Casos de uso recomendados

Usar `MCP` cuando:

- el consumidor principal es un LLM o agente
- quieres exponer herramientas semiestructuradas en vez de integrar REST manualmente
- necesitas tanto texto legible como `structuredContent`

Usar `API` normal cuando:

- integras con otro backend o servicio propio
- necesitas control fino de errores, reintentos y versionado de contrato
- no trabajas con clientes MCP

## Ejemplos conceptuales de uso

`consulta_fiscal`:

- pregunta: `modelo 216 como rellenar`
- entrada: `q` obligatorio, con `sujeto`, `pais` y `tipo_operacion` opcionales
- salida: texto resumido para el LLM y contenido estructurado subyacente

`listar_obligaciones_aplicables`:

- perfil por defecto: `sociedad_valores`
- flags utiles: `reporting_reservado`, `aml_cft_reforzado`, `cross_border_ue`

`get_obligacion_completa`:

- entrada: codigo de obligacion
- utilidad: recuperar plazos, sanciones, recargos y documentos relacionados

## Regla de seguridad

No tratar `MCP` como una superficie publica abierta por defecto.

No tratar tampoco la respuesta del MCP como verdad autosuficiente.

Para uso interno correcto:

- si la respuesta incluye aviso de evidencia insuficiente, no usarla para decidir sin revisar fuente oficial
- si la herramienta devuelve pocos o ningun resultado, eso debe interpretarse como abstencion, no como confirmacion negativa del hecho consultado
- las decisiones fiscales o regulatorias deben verificarse contra la fuente oficial citada o contra el endpoint REST equivalente

Si se expone por HTTP fuera de local o red controlada, revisar al menos:

- `MCP_API_KEY`
- `MCP_RATE_LIMIT_PER_MINUTE`
- proxy o perimetro delante del servicio
- logs y observabilidad

## Referencias

- `../../apps/api/mcp_server.py`
- `../../apps/api/mcp_catalog.py`
- `../../apps/api/mcp_stdio.py`
- `../../apps/api/tests/test_mcp_private.py`
