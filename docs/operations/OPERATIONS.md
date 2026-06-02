# Operations

## Objetivo

Operacion diaria minima de `esdata` para un despliegue privado con Docker Compose y scheduler externo para jobs `cron-*`.

## Componentes a vigilar

- `postgres`
- `api`
- `web`
- `caddy`
- workers continuos del deploy canonico (`worker-boe`, `worker-dgt`, `worker-teac`, `worker-modelos`, `worker-bdns`, `worker-borme`, `worker-cnmv`, `worker-sepblac`, `worker-cendoj`, `worker-eurlex`, `worker-bde`, `worker-aepd`)
- jobs `cron-*` si el entorno los programa externamente

## Comprobaciones rapidas

Los ejemplos con `curl` asumen que `ESDATA_API_KEY` y `MCP_API_KEY` ya estan exportadas en la shell actual o se sustituyen inline desde `/etc/esdata/esdata.env`.

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml ps
curl http://127.0.0.1:8000/health
curl -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/status
curl -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/v1/modelos
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" http://127.0.0.1:8000/mcp
```

## Logs

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs -f api
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs -f postgres
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs -f worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd
```

## Operaciones frecuentes

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml restart api
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml restart worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d --build api web
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml down
```

## Cambios de configuracion

Cuando cambie el fichero de entorno:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml config
bash scripts/ops/deploy-hetzner.sh
```

Si solo necesitas recrear el runtime continuo tras un cambio ya migrado y verificado:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd
```

## Base de datos y migraciones

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml build ops
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic current
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d --build api
```

Si el commit cambia `alembic/`, `scripts/maintenance/` empaquetado en `ops` o codigo copiado a la imagen `api`, no uses solo `restart api`. Reconstruye `ops` antes de ejecutar Alembic y recrea `api` con `up -d --build api` despues de migrar. Una imagen `api` antigua puede entrar en restart loop si la base queda en una revision Alembic que la imagen no contiene.

## Backup minimo

Usar el script oficial:

```bash
ENV_FILE=/etc/esdata/esdata.env BACKUP_DIR=/srv/backups/esdata scripts/ops/backup-postgres.sh
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
