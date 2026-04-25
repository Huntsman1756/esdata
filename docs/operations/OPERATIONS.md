# Operations

## Objetivo

Este documento describe la operacion diaria minima de `esdata` para un despliegue privado con Docker Compose.

Sirve para:

- el owner del proyecto durante la fase de prueba
- IT cuando el servicio pase a un servidor mejor

## Componentes a vigilar

- `api`
- `postgres`
- `web` si aplica
- `worker-boe`
- `worker-dgt`
- `worker-teac`
- `worker-modelos`
- `caddy` si se expone por dominio

## Comprobaciones rapidas

### Salud de contenedores

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml ps
```

### API

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
curl http://127.0.0.1:8000/v1/modelos
```

### MCP privado

```bash
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" http://127.0.0.1:8000/mcp
```

Se espera cabecera `mcp-session-id`.

## Logs

### API

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml logs -f api
```

### Postgres

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml logs -f postgres
```

### Workers

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml logs -f worker-boe worker-dgt worker-teac worker-modelos
```

## Operaciones frecuentes

### Reiniciar solo API

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml restart api
```

### Reiniciar workers

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml restart worker-boe worker-dgt worker-teac worker-modelos
```

### Recrear API tras cambio de imagen o build

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml up -d --build api
```

### Parar el stack

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml down
```

## Cambios de configuracion

Cuando cambie `infra/deploy/.env`:

1. editar el fichero
2. validar el compose
3. recrear solo los servicios afectados

```bash
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml config
docker compose --env-file infra/deploy/.env -f infra/deploy/docker-compose.prod.yml up -d api caddy
```

## Backups minimos

Si Postgres vive en el mismo host:

```bash
docker exec -t <postgres-container> pg_dump -U esdata esdata > backup-esdata.sql
```

Frecuencia minima recomendada:

- backup diario
- retencion minima de 7 dias

## Incidencias comunes

### `/mcp` devuelve `401`

Comprobar:

- que `MCP_API_KEY` esta definida en `infra/deploy/.env`
- que el cliente envia `X-API-Key`
- que se recreo `api` tras cambiar variables

### `/mcp` devuelve `429`

Comprobar:

- valor de `MCP_RATE_LIMIT_PER_MINUTE`
- si hay polling excesivo del cliente

### `/health` falla

Comprobar:

- logs de `api`
- conectividad a Postgres
- valor de `DATABASE_URL`

### Workers sin progreso

Comprobar:

- logs de cada worker
- conectividad saliente a BOE/DGT/TEAC/AEAT
- que las variables de seed y SSL son correctas

## Verificacion despues de cambios

Desde el repo:

```bash
pytest apps/api/tests/test_mcp_private.py -q
pytest apps/api/tests/test_smoke.py -q
```

En el host:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
```

## Referencias

- `docs/operations/LOGGING.md`
- `docs/operations/DATA-POLICY.md`
- `docs/operations/DEPENDENCIES.md`
- `docs/operations/SECRETS.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/deployment/vps-trial-deploy.md`
- `docs/deployment/HANDOFF-IT.md`
- `docs/environment-variables.md`
