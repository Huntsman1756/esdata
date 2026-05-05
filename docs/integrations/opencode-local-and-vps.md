# OpenCode + HTTP MCP (local y VPS)

## Objetivo

Configurar `OpenCode` para consumir `esdata` por `HTTP MCP` via `url` hacia `/mcp`.

## Alcance exacto

Esta guia cubre solo `OpenCode` contra `HTTP MCP` montado en `/mcp`.

No cubre `stdio MCP`, `command`, `args` ni clientes que arranquen procesos hijo.

Regla practica:

- `OpenCode` configurado por `url` usa `HTTP MCP`
- no asumir que las tools de `stdio` estan disponibles en `/mcp`
- para `OpenCode`, la frontera en esta guia es siempre `URL -> /mcp`

## Contrato local

- URL: `http://127.0.0.1:8000/mcp`
- Header: `X-API-Key: <MCP_API_KEY>`

Ejemplo de config local para `OpenCode`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "esdata-local": {
      "type": "remote",
      "url": "http://127.0.0.1:8000/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {
        "X-API-Key": "{env:MCP_API_KEY}"
      }
    }
  }
}
```

## Contrato VPS

- URL: `https://api.tudominio/mcp`
- Header: `X-API-Key: <MCP_API_KEY>`

Ejemplo de config remota para `OpenCode`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "esdata": {
      "type": "remote",
      "url": "https://api.tudominio/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {
        "X-API-Key": "{env:MCP_API_KEY}"
      }
    }
  }
}
```

## Verificacion opcional

`OpenCode` gestiona el handshake MCP una vez que el servidor queda configurado por `url` y `headers`.

Si quieres comprobar manualmente que el endpoint responde:

```bash
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" https://api.example.internal/mcp
```

En este stack, una primera llamada valida puede responder `400 Missing session ID` y aun asi indicar que el endpoint MCP esta sano.

Comprobacion rapida adicional:

- `opencode mcp list` debe mostrar el servidor configurado

## Notas

- `OpenCode` usa `MCP_API_KEY`, no `ESDATA_API_KEY`
- esta guia asume `OpenCode` consumiendo `HTTP MCP` por `url`
- para limites de `HTTP MCP` frente a `stdio`, ver `docs/manual-usuario/07-mcp-y-clientes.md`

## Que no cubre este documento

- arranque del backend
- despliegue del servidor
- integraciones `stdio`
