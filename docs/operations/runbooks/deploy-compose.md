# Runbook: Deploy con Docker Compose

## Objetivo

Levantar `esdata` en un servidor usando `infra/deploy/docker-compose.prod.yml` y el contenedor `ops` como runner oficial de migraciones/verificaciones.

## Prerrequisitos

- Docker Engine y Docker Compose v2
- fichero de entorno externo o `infra/deploy/.env.prod` basado en `infra/deploy/compose.env.example`
- salida HTTPS a BOE, DGT, TEAC, CNMV, SEPBLAC, BDE y fuentes activadas

## Pasos

1. preparar el fichero de entorno
2. validar el compose
3. levantar `postgres`
4. ejecutar migraciones y `verify_schema`
5. levantar `api`, `web`, `caddy` y workers base
6. verificar `/health`, `/status` y rutas web principales

## Comandos

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml config
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
```

## Cron jobs

Los servicios `cron-*` son jobs one-shot y necesitan scheduler externo.

Nota operativa: en produccion es normal ver contenedores `deploy-cron-*` en `Exited (0)` despues de una ejecucion correcta.

Ejemplos manuales:

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-boe-daily
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-dgt-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-teac-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-modelos-daily
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-bdns-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-borme-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-cnmv-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-sepblac-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-bde-weekly
```

## Alertmanager y Telegram

`infra/observability/alertmanager.yml` es una plantilla del repo. En el VPS debe existir una version renderizada con `bot_token` y `chat_id` reales antes de reiniciar `deploy-alertmanager-1`.

No copiar la plantilla sin renderizar sobre `/srv/esdata/infra/observability/alertmanager.yml` y reiniciar despues, porque `chat_id: ${TELEGRAM_CHAT_ID}` hace que Alertmanager no arranque al esperar un entero real.

## Verificaciones post-deploy

1. `docker compose ... ps`
2. `curl /health`
3. `curl /status`
4. comprobar `sync_log`
5. revisar logs de `api` y workers activos
6. `systemctl list-timers --all | grep esdata`
7. `curl http://127.0.0.1:8000/metrics | grep worker_last_errors`
8. `docker exec deploy-alertmanager-1 wget -qO- http://127.0.0.1:9093/api/v2/alerts/groups`
