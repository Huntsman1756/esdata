# VPS Trial Deploy

## Objetivo

Levantar `esdata` en un VPS pequeno para validar el servicio antes de pasarlo a infraestructura corporativa.

Este documento esta pensado para:

- una primera instalacion por parte del owner del proyecto
- un unico servidor Ubuntu
- despliegue con Docker Compose
- uso privado de `/mcp`

No esta pensado para despliegue publico abierto ni para una topologia enterprise final.

## Arquitectura recomendada para la prueba

- 1 VPS Ubuntu 24.04
- Docker Engine + Docker Compose plugin
- `infra/deploy/docker-compose.prod.yml`
- `api`, `postgres`, `web`, `caddy` y los workers necesarios
- acceso a `/mcp` solo desde red privada, VPN o un proxy con restriccion de acceso

## Tamano recomendado del VPS

Minimo razonable para prueba:

- 2 vCPU
- 4 GB RAM
- 40 GB SSD

Si vas a correr API, web, Postgres y varios workers a la vez, mejor:

- 4 vCPU
- 8 GB RAM
- 80 GB SSD

## Prerrequisitos

- acceso SSH al VPS
- usuario con permisos `sudo`
- Docker y Compose instalados
- DNS o acceso directo por IP
- copia local del repo en la revision deseada

## Variables necesarias

Variables minimas para este corte:

- `DATABASE_URL`
- `POSTGRES_PASSWORD`
- `ESDATA_API_BASE_URL`
- `API_DOMAIN`
- `WEB_DOMAIN`
- `TEAC_SEED_URLS`
- `MCP_API_KEY`
- `MCP_RATE_LIMIT_PER_MINUTE`

Variables utiles adicionales:

- `APP_ENV=production`
- `BOE_LEGISLACION_NORMAS`
- `DGT_SSL_VERIFY`
- `MODELOS_SYNC_INTERVAL`

## Paso a paso

### 1. Preparar el servidor

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl git
```

Instalar Docker siguiendo la guia oficial o el estandar de tu entorno.

Verificar:

```bash
docker --version
docker compose version
```

### 2. Copiar el repo al VPS

```bash
git clone <repo-url> esdata
cd esdata
git checkout feat/mcp-privado-fiable
```

Si vas a desplegar desde otra rama o desde `main`, sustituir la referencia.

### 3. Preparar el fichero de entorno

Crear `infra/deploy/.env` a partir de `infra/deploy/compose.env.example`.

Variables a revisar como minimo en ese fichero:

```env
APP_ENV=production

POSTGRES_USER=esdata
POSTGRES_PASSWORD=<cambiar>
POSTGRES_DB=esdata
DATABASE_URL=postgresql+psycopg://esdata:<cambiar>@postgres:5432/esdata

API_DOMAIN=api.example.internal
WEB_DOMAIN=web.example.internal
ESDATA_API_BASE_URL=https://api.example.internal
CADDY_EMAIL=ops@example.com

TEAC_SEED_URLS=https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/criterio.aspx?id=...

MCP_API_KEY=<cambiar>
MCP_RATE_LIMIT_PER_MINUTE=60
```

## Importante sobre MCP

Para esta fase de prueba:

- no publicar `/mcp` abierto a Internet
- usar red privada, Tailscale, VPN o proxy con restriccion de acceso
- mantener `MCP_API_KEY` fuera del repo y fuera de variables publicas

### 4. Validar el compose

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml config
```

Debe resolver sin errores.

### 5. Levantar servicios base

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml up -d postgres api web caddy
```

Si quieres validar solo API + MCP primero:

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml up -d postgres api
```

### 6. Levantar workers necesarios

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml up -d worker-boe worker-dgt worker-teac worker-modelos
```

No hace falta levantar todos los workers documentales el primer dia si quieres una prueba mas controlada.

### 7. Verificar salud

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
```

Esperado:

- API sana
- Postgres sano
- web respondiendo si fue levantada

### 8. Verificar MCP privado

Handshake:

```bash
curl -i \
  -H "Accept: text/event-stream" \
  -H "X-API-Key: $MCP_API_KEY" \
  http://127.0.0.1:8000/mcp
```

Debe devolver cabecera `mcp-session-id`.

`initialize`:

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
      "clientInfo": {"name": "manual", "version": "1.0"}
    }
  }' \
  http://127.0.0.1:8000/mcp
```

`tools/list`:

```bash
curl -s \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $MCP_API_KEY" \
  -H "MCP-Session-ID: <session-id>" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}' \
  http://127.0.0.1:8000/mcp
```

### 9. Verificaciones del repo antes de darlo por bueno

Desde el repo:

```bash
pytest apps/api/tests/test_mcp_private.py -q
pytest apps/api/tests/test_smoke.py -q
```

## Criterio de exito para la prueba en VPS

1. `/health` responde `200`
2. `/status` responde `200`
3. `/mcp` exige `X-API-Key` cuando `MCP_API_KEY` esta configurada
4. `initialize` y `tools/list` funcionan sobre `/mcp`
5. logs sin reinicios continuos de contenedores

## Siguientes pasos tras validar la prueba

1. estabilizar configuracion final de variables
2. decidir si Postgres queda en el mismo host o pasa a servicio gestionado
3. pasar el handoff a IT con `docs/operations/OPERATIONS.md` y `docs/deployment/HANDOFF-IT.md`
