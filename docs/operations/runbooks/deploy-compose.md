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
5. levantar `api`, `web`, `caddy` y todos los workers continuos requeridos
6. verificar `/health`, `/status` y rutas web principales

## Comandos

```bash
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml config
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops python scripts/maintenance/verify_schema.py
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml up -d api web caddy worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
```

## Cron jobs

Los servicios `cron-*` son jobs one-shot y necesitan scheduler externo.

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
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-cendoj-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-aepd-weekly
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml run --rm cron-eurlex-weekly
```

## Timers systemd

Los `cron-*` solo quedan programados de verdad cuando se instala `esdata-job@.service` y se habilitan los `.timer` de `infra/deploy/systemd/`.

Validacion operativa minima:

1. el unit instalado debe ejecutar `docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i` sin `--no-deps`
2. `WorkerSilent` debe evaluarse sobre `worker_stale_status`, no sobre una ventana fija de `48h`
3. tras cambiar `infra/observability/alerts.yml`, hay que recrear `prometheus` o recargar explicitamente sus reglas en el host
4. antes de validar alertas, invocar `/status` una vez para refrescar las metricas `worker_stale_status` derivadas de `sync_log`

Comando recomendado de chequeo:

```bash
python scripts/ops/worker_scheduler_guard.py check --repo-root /srv/esdata --installed-unit /etc/systemd/system/esdata-job@.service
```

```bash
sudo cp infra/deploy/systemd/esdata-job@.service /etc/systemd/system/
sudo cp infra/deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esdata-boe-daily.timer esdata-modelos-daily.timer esdata-dgt-weekly.timer esdata-teac-weekly.timer esdata-bdns-weekly.timer esdata-borme-weekly.timer esdata-cnmv-weekly.timer esdata-sepblac-weekly.timer esdata-bde-weekly.timer esdata-cendoj-weekly.timer esdata-aepd-weekly.timer esdata-eurlex-weekly.timer
systemctl cat esdata-job@.service
systemctl list-timers --all | grep esdata
```

## Verificaciones post-deploy

1. `docker compose ... ps`
2. `curl /health`
3. `curl /status`
4. comprobar `sync_log`
5. revisar logs de `api` y workers activos
