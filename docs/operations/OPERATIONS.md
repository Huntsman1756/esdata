# Operations

## Objetivo

Operacion diaria minima de `esdata` para un despliegue privado con Docker Compose y scheduler externo para jobs `cron-*`.

## Componentes a vigilar

- `postgres`
- `api`
- `web`
- `caddy`
- workers continuos activados (`worker-boe`, `worker-dgt`, `worker-teac`, `worker-modelos` y los adicionales que se hayan habilitado)
- jobs `cron-*` si el entorno los programa externamente

## Comprobaciones rapidas

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
curl -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/v1/modelos
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" http://127.0.0.1:8000/mcp
```

## Logs

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml logs -f api
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml logs -f postgres
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml logs -f worker-boe worker-dgt worker-teac worker-modelos
```

## Operaciones frecuentes

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml restart api
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml restart worker-boe worker-dgt worker-teac worker-modelos
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d --build api web
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml down
```

## Cambios de configuracion

Cuando cambie el fichero de entorno:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml config
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d api web caddy
```

## Base de datos y migraciones

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic current
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade heads
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
```

## Backup minimo

Usar el script oficial:

```bash
ENV_FILE=infra/deploy/.env.prod BACKUP_DIR=/srv/backups/esdata scripts/ops/backup-postgres.sh
```

## Incidencias comunes

### `/mcp` devuelve `401`

- comprobar `MCP_API_KEY`
- comprobar cabecera `X-API-Key`
- recrear `api` si cambian variables

### `/health` falla

- revisar logs de `api`
- comprobar `DATABASE_URL`
- comprobar estado de `postgres`

### Workers sin progreso

- revisar logs
- revisar `sync_log`
- comprobar seeds y conectividad externa

## Referencias

- `docs/operations/README.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/operations/runbooks/backup-restore.md`
- `docs/operations/runbooks/worker-aeat.md`
- `docs/environment-variables.md`
