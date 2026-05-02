# OpenCode + MCP (local y VPS)

## Objetivo

Documentar el flujo personal de uso de `esdata` como servidor MCP para `OpenCode` con un modelo LLM local.

Este documento cubre dos modos:

- uso local en tu maquina
- uso remoto privado desde un VPS

## Arquitectura recomendada

### Modo local

- `OpenCode` corre en tu maquina
- tu modelo LLM corre localmente
- `esdata` corre local o en Docker local
- `OpenCode` consume `/mcp` en `localhost`

Ventajas:

- menor latencia
- cero dependencia de Internet para el flujo base
- ideal para iterar prompts, tools y consultas

### Modo VPS privado

- `OpenCode` sigue siendo el cliente
- el modelo puede seguir siendo local
- `esdata` corre en un VPS privado
- `OpenCode` consume `/mcp` a traves de HTTPS o red privada

Ventajas:

- validas un entorno mas parecido a produccion
- pruebas auth, red, Docker y despliegue real
- no dependes de tener toda la data o servicios siempre en tu maquina local

## Recomendacion practica

Usar ambos:

1. local para desarrollo diario
2. VPS privado para pruebas mas realistas y sesiones remotas

## Requisitos minimos

- `esdata` levantado
- endpoint `/mcp` disponible
- `MCP_API_KEY` configurada cuando el servicio no sea estrictamente local
- `OpenCode` configurado para llamar al endpoint MCP correcto

## Modo local

### Levantar la API localmente

Ejemplo de desarrollo:

```bash
pytest apps/api/tests/test_smoke.py -q
pytest apps/api/tests/test_mcp_private.py -q
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Si prefieres contenedor:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres api
```

### Verificar MCP local

```bash
curl -i -H "Accept: text/event-stream" http://127.0.0.1:8000/mcp
```

Si `MCP_API_KEY` esta activa, anadir:

```bash
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" http://127.0.0.1:8000/mcp
```

### Configurar OpenCode

La configuracion exacta depende del cliente MCP de `OpenCode`, pero el contrato operativo es este:

- endpoint MCP: `http://127.0.0.1:8000/mcp`
- cabecera opcional: `X-API-Key`
- handshake MCP por `text/event-stream`

Si `OpenCode` permite definir un servidor MCP HTTP, usa:

- URL: `http://127.0.0.1:8000/mcp`
- Header: `X-API-Key: <tu-clave>` solo si activaste proteccion local

## Modo VPS privado

### Despliegue

Seguir:

- `docs/deployment/vps-trial-deploy.md`

### Exposicion recomendada

Para uso personal:

- Tailscale o VPN, o
- HTTPS privado con dominio controlado, o
- IP pública restringida y `MCP_API_KEY`

Evitar:

- exponer `/mcp` abierto a Internet sin control adicional

### Configuracion de OpenCode contra VPS

Contrato esperado:

- endpoint MCP: `https://api.tudominio/mcp` o `https://mcp.tudominio/`
- cabecera: `X-API-Key: <tu-clave>`

Ejemplo verificado en VPS Arsys:

- URL: `https://api.desuscribir.es/mcp`
- Header: `X-API-Key: <MCP_API_KEY>`

Ejemplo de config remota para `OpenCode`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "esdata": {
      "type": "remote",
      "url": "https://api.desuscribir.es/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {
        "X-API-Key": "{env:ESDATA_MCP_API_KEY}"
      }
    }
  }
}
```

Notas:

- `OpenCode` usa `MCP_API_KEY`, no `ESDATA_API_KEY`
- `opencode mcp list` debe mostrar el servidor remoto configurado

## Verificaciones utiles

### Handshake

```bash
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" https://api.example.internal/mcp
```

### Initialize

```bash
curl -s \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $MCP_API_KEY" \
  -H "MCP-Session-ID: <session-id>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {"name": "OpenCode", "version": "1.0"}
    }
  }' \
  https://api.example.internal/mcp
```

## Buenas practicas

- usa una key distinta para tu entorno personal y para entornos compartidos
- manten el MCP local aunque tambien tengas VPS, porque te da un fallback muy rapido
- usa el VPS para validar cambios relevantes antes de pasarlos a IT

## Que no cubre este documento

- integracion con `ChatGPT Business`
- despliegue corporativo final

Para eso ver:

- `docs/integrations/chatgpt-business-actions.md`
- `docs/deployment/HANDOFF-IT.md`
